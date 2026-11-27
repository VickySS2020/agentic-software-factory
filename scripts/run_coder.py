from __future__ import annotations

import asyncio
import json
import os
import subprocess
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

from factory_app.agents import coder_agent  # noqa: E402

RUNS = ROOT / "runs"


def ensure_branch(change_id: str) -> str:
    """Ensure the repo is on an isolated branch cr/<change_id> for the Coder agent."""
    target_branch = f"cr/{change_id}"
    res = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    current_branch = res.stdout.strip()
    if current_branch == target_branch:
        return target_branch

    # Check if branch exists
    check_branch = subprocess.run(
        ["git", "rev-parse", "--verify", target_branch],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check_branch.returncode == 0:
        subprocess.run(["git", "checkout", target_branch], cwd=ROOT, check=True)
    else:
        subprocess.run(["git", "checkout", "-b", target_branch], cwd=ROOT, check=True)
    print(f"[GIT] Switched to branch: {target_branch}")
    return target_branch


async def _run_agent_with_retry(
    agent,
    prompt: str,
    user_id: str,
    session_id: str,
    initial_state: dict | None = None,
    max_retries: int = 4,
) -> str:
    """Execute an ADK agent with in-memory runner and exponential backoff on transient errors."""
    runner = InMemoryRunner(agent=agent)
    for attempt in range(1, max_retries + 1):
        curr_session_id = f"{session_id}_try_{attempt}"
        try:
            await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=user_id,
                session_id=curr_session_id,
                state=initial_state or {},
            )
            output_parts: list[str] = []
            msg = types.Content(parts=[types.Part.from_text(text=prompt)])
            async for event in runner.run_async(
                user_id=user_id, session_id=curr_session_id, new_message=msg
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
            retryable = (
                "503" in err_msg
                or "429" in err_msg
                or "UNAVAILABLE" in err_msg
                or "ResourceExhausted" in err_msg
            )
            if retryable and attempt < max_retries:
                wait_time = 15 * attempt
                print(
                    f"[RETRY] Upstream rate limit or transient error ({err_msg[:60]}...). "
                    f"Retrying in {wait_time}s (attempt {attempt}/{max_retries})..."
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


def run_coder(change_id: str) -> int:
    run_dir = RUNS / change_id
    if not run_dir.exists():
        print(f"Error: Run directory {run_dir} does not exist.")
        print(f"Run 'python scripts/start_run.py {change_id}' first.")
        return 1

    state_file = run_dir / "factory-state.json"
    if not state_file.exists():
        print(f"Error: factory-state.json missing in {run_dir}")
        return 1

    state = json.loads(state_file.read_text(encoding="utf-8"))
    human_gates = state.get("human_gates", {})

    # Human Gate Check: Plan must be APPROVED
    if human_gates.get("plan") != "APPROVED" or state.get("status") not in {
        "PLAN_APPROVED",
        "CODING_RUNNING",
    }:
        print("\n[GATE BLOCKED] Implementation plan has not been APPROVED by human gatekeeper.")
        print(f"Current status: {state.get('status')}")
        print(f"Plan gate decision: {human_gates.get('plan')}")
        print("To approve the plan, run:")
        print(f'  python scripts/approve_gate.py {change_id} plan APPROVED "<reason>"')
        return 1

    plan_path = run_dir / "02-implementation-plan.md"
    if not plan_path.exists():
        print(f"Error: Missing approved implementation plan at {plan_path}")
        return 1

    cr_path = run_dir / "00-change-request.md"
    cr_text = cr_path.read_text(encoding="utf-8") if cr_path.exists() else ""
    plan_text = plan_path.read_text(encoding="utf-8")

    decision_path = run_dir / "03-human-plan-decision.json"
    decision_text = decision_path.read_text(encoding="utf-8") if decision_path.exists() else "{}"

    # Ensure isolated branch
    branch_name = ensure_branch(change_id)
    print(f"\n=== Running Coder Agent for {change_id} on {branch_name} ===")
    update_state(run_dir, status="CODING_RUNNING")

    coder_prompt = (
        f"Active Change Request: {change_id}\n\n"
        f"Change Request Specification:\n{cr_text}\n\n"
        f"Human Plan Decision:\n{decision_text}\n\n"
        f"Approved Implementation Plan:\n{plan_text}\n\n"
        "Instructions for Coder:\n"
        "1. Read repository files using `read_repo_file` to inspect existing code and tests.\n"
        "2. Implement only the changes detailed in the approved plan using `write_code_file`.\n"
        "   - You may only write to `campusflow/` and `tests/`.\n"
        "   - Ensure all acceptance criteria are met.\n"
        "3. Run verification using `run_limited_command('pytest -q')` and `ruff check`.\n"
        "4. Produce and save `coder-report.md` via `write_coder_report` summarizing:\n"
        "   - Changes implemented in domain, repository, and service\n"
        "   - Mapping to acceptance criteria\n"
        "   - Verification command results (pytest & ruff)\n"
        "   - Confirmation that only approved files were modified."
    )

    coder_result = asyncio.run(
        _run_agent_with_retry(
            agent=coder_agent,
            prompt=coder_prompt,
            user_id="factory_runner",
            session_id=f"coder_{change_id}_{int(time.time())}",
            initial_state={"approved_plan": plan_text},
        )
    )

    # Ensure coder-report is persisted in runs/<change_id>/
    coder_report_path = run_dir / "coder-report.md"
    if not coder_report_path.exists():
        coder_report_path.write_text(coder_result, encoding="utf-8")
        (run_dir / "04-coder-report.md").write_text(coder_result, encoding="utf-8")

    update_state(run_dir, status="CODING_COMPLETED")
    print(f"\n[DONE] Coding stage complete. Report saved -> {coder_report_path.relative_to(ROOT)}")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/run_coder.py CR-001")
    change_id = sys.argv[1].strip().upper()
    exit_code = run_coder(change_id)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
