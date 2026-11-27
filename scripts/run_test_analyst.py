from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

load_dotenv()

# Ensure Google genai recognizes GEMINI_API_KEY
if "GEMINI_API_KEY" in os.environ and "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory_app.agents import test_analyst_agent  # noqa: E402
from factory_app.tools import get_coder_diff  # noqa: E402

RUNS = ROOT / "runs"


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


def run_test_analyst(change_id: str) -> int:
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
    status = state.get("status")

    # Gate Check: Coder must have completed
    coder_report_path = run_dir / "04-coder-report.md"
    if not coder_report_path.exists():
        coder_report_path = run_dir / "coder-report.md"

    valid_statuses = {"CODING_COMPLETED", "TEST_ANALYSIS_RUNNING"}
    if not coder_report_path.exists() or status not in valid_statuses:
        print("\n[GATE BLOCKED] Coder stage has not completed. Cannot run Test Analyst.")
        print(f"Current status: {status}")
        print("Run the coder agent first using:")
        print(f"  python scripts/run_coder.py {change_id}")
        return 1

    cr_path = run_dir / "00-change-request.md"
    cr_text = cr_path.read_text(encoding="utf-8") if cr_path.exists() else ""

    plan_path = run_dir / "02-implementation-plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

    coder_text = coder_report_path.read_text(encoding="utf-8")

    diff_info = get_coder_diff(change_id)
    coder_diff = diff_info.get("diff", "")

    print(f"\n=== Running Test Analyst Agent for {change_id} ===")
    update_state(run_dir, status="TEST_ANALYSIS_RUNNING")

    prompt = (
        f"Active Change Request: {change_id}\n\n"
        f"Change Request Specification:\n{cr_text}\n\n"
        f"Approved Implementation Plan:\n{plan_text}\n\n"
        f"Coder Report:\n{coder_text}\n\n"
        f"Coder Git Diff:\n{coder_diff}\n\n"
        "Instructions for Test Analyst:\n"
        "1. Analyze only the changes made by the Coder Agent.\n"
        "2. Identify missing test gaps (negative cases, boundary values, error paths).\n"
        "3. Propose and write only authorized tests under `tests/` using `write_test_file`.\n"
        "   - You CANNOT modify application code (campusflow/ or src/).\n"
        "4. Run tests with `run_limited_command('pytest -q')` to verify new tests run cleanly.\n"
        "5. Do NOT determine final PASS or declare release readiness.\n"
        "6. Produce and save `05-test-analysis.md` via `write_test_analysis_report` detailing:\n"
        "   - Analyzed Coder Changes\n"
        "   - Identified Test Gaps (Negative, Boundary, Regression)\n"
        "   - Authorized Tests Added\n"
        "   - Deterministic Execution Evidence (raw pytest output, no release declaration)."
    )

    analyst_result = asyncio.run(
        _run_agent_with_retry(
            agent=test_analyst_agent,
            prompt=prompt,
            user_id="factory_runner",
            session_id=f"test_analyst_{change_id}_{int(time.time())}",
            initial_state={"coder_report": coder_text, "coder_diff": coder_diff},
        )
    )

    # Ensure 05-test-analysis.md is persisted in runs/<change_id>/
    analysis_report_path = run_dir / "05-test-analysis.md"
    if not analysis_report_path.exists():
        analysis_report_path.write_text(analyst_result, encoding="utf-8")
        (run_dir / "test-analysis.md").write_text(analyst_result, encoding="utf-8")

    update_state(run_dir, status="TEST_ANALYSIS_COMPLETED")
    rel_path = analysis_report_path.relative_to(ROOT)
    print(f"\n[DONE] Test analysis complete. Report saved -> {rel_path}")
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/run_test_analyst.py CR-001")
    change_id = sys.argv[1].strip().upper()
    exit_code = run_test_analyst(change_id)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
