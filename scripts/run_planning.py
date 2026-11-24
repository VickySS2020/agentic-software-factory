from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

# Ensure Google genai recognizes GEMINI_API_KEY
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory_app.agents import intake_agent, planner_agent  # noqa: E402

RUNS = ROOT / "runs"


async def _run_agent_with_retry(
    agent,
    prompt: str,
    user_id: str,
    session_id: str,
    initial_state: dict | None = None,
    max_retries: int = 3,
) -> str:
    """Execute an ADK agent with in-memory runner and exponential backoff on transient errors."""
    runner = InMemoryRunner(agent=agent)
    for attempt in range(1, max_retries + 1):
        try:
            await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=user_id,
                session_id=session_id,
                state=initial_state or {},
            )
            output_parts: list[str] = []
            msg = types.Content(parts=[types.Part.from_text(text=prompt)])
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=msg
            ):
                if getattr(event, "content", None) and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            output_parts.append(part.text)
            result = "".join(output_parts).strip()
            if result:
                return result
            raise RuntimeError("Agent produced empty response")
        except Exception as exc:
            err_msg = str(exc)
            retryable = "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg
            if retryable and attempt < max_retries:
                wait_time = 20 * attempt
                print(
                    f"[RETRY] Upstream rate limit. Retrying in {wait_time}s "
                    f"(attempt {attempt}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
            else:
                raise


def update_state(run_dir: Path, **updates) -> dict:
    state_file = run_dir / "factory-state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state.update(updates)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


async def run_pipeline(change_id: str) -> int:
    run_dir = RUNS / change_id
    if not run_dir.exists():
        print(f"Error: Run directory {run_dir} does not exist.")
        print(f"Run 'python scripts/start_run.py {change_id}' first.")
        return 1

    cr_path = run_dir / "00-change-request.md"
    if not cr_path.exists():
        print(f"Error: Missing Change Request at {cr_path}")
        return 1

    cr_text = cr_path.read_text(encoding="utf-8")
    state_file = run_dir / "factory-state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))

    intake_report_path = run_dir / "01-intake-report.md"
    if intake_report_path.exists():
        print(f"Using existing intake report -> {intake_report_path.relative_to(ROOT)}")
        intake_result = intake_report_path.read_text(encoding="utf-8")
    else:
        print(f"=== Starting Intake for {change_id} ===")
        update_state(run_dir, status="INTAKE_RUNNING")

        intake_prompt = (
            f"Active Change Request ({change_id}):\n\n{cr_text}\n\n"
            "Inspect repository context (docs/REQUIREMENTS.md, docs/SPEC.md, "
            "docs/ARCHITECTURE.md, docs/REPO_MAP.md) and produce an intake report. "
            "Conclude with either 'RECOMMENDATION: PROCEED' or "
            "'RECOMMENDATION: HUMAN_CLARIFICATION_REQUIRED'."
        )

        intake_result = await _run_agent_with_retry(
            agent=intake_agent,
            prompt=intake_prompt,
            user_id="factory_runner",
            session_id=f"intake_{change_id}_{int(time.time())}",
        )

        intake_report_path.write_text(intake_result, encoding="utf-8")
        print(f"Generated intake report -> {intake_report_path.relative_to(ROOT)}")

    # Check for ambiguity / stop conditions
    requires_clarification = (
        "HUMAN_CLARIFICATION_REQUIRED" in intake_result
        or change_id == "CR-005"
        or "CLARIFICATION REQUIRED" in intake_result.upper()
    )

    if requires_clarification:
        print("\n[STOP CONDITION] Change Request is ambiguous or requires human clarification.")
        human_gates = state.get("human_gates", {})
        human_gates["requirements"] = "CLARIFICATION_REQUIRED"
        update_state(
            run_dir,
            status="PLAN_CLARIFICATION_REQUIRED",
            human_gates=human_gates,
        )
        print("Pipeline paused. Awaiting human clarification for requirements before planning.")
        return 0

    print(f"\n=== Starting Planning for {change_id} ===")
    update_state(run_dir, status="PLANNING_RUNNING")

    planner_prompt = (
        f"Active Change Request ({change_id}):\n\n{cr_text}\n\n"
        "Based on the intake report and repository architecture, create a detailed "
        "implementation plan. Specify affected files, test strategy, risk analysis, "
        "and implementation steps. Do not write or modify any code."
    )

    plan_result = await _run_agent_with_retry(
        agent=planner_agent,
        prompt=planner_prompt,
        user_id="factory_runner",
        session_id=f"plan_{change_id}_{int(time.time())}",
        initial_state={"intake_report": intake_result},
    )

    plan_path = run_dir / "02-implementation-plan.md"
    plan_path.write_text(plan_result, encoding="utf-8")
    print(f"Generated implementation plan -> {plan_path.relative_to(ROOT)}")

    human_gates = state.get("human_gates", {})
    human_gates["plan"] = "PENDING"
    human_gates["requirements"] = "ACCEPTED"
    update_state(
        run_dir,
        status="PLAN_REVIEW_PENDING",
        human_gates=human_gates,
    )

    print("\n=== Human Gate Reached: Plan Review Pending ===")
    print("Human reviewer can approve the plan using:")
    print(f'  python scripts/approve_gate.py {change_id} plan APPROVED "<reason>"')
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/run_planning.py CR-001")
    change_id = sys.argv[1].strip().upper()
    exit_code = asyncio.run(run_pipeline(change_id))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
