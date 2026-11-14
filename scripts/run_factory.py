"""Script-driven factory pipeline runner.

Usage
-----
  # 1. Initialise a run (creates runs/CR-001/factory-state.json via start_run.py first)
  python scripts/run_factory.py CR-001

  # 2. Resume after human plan approval
  #    (approve_gate.py CR-001 plan APPROVED "looks good")
  python scripts/run_factory.py CR-001

The script advances the pipeline one stage at a time, persisting state between
calls so it is safe to restart. Each LLM stage is invoked through the ADK Runner.
Deterministic gates (VerificationGate) run as plain Python — no LLM.

Pipeline stages (status values in factory-state.json)
------------------------------------------------------
  INTAKE_PENDING      -> IntakeAgent       -> INTAKE_DONE | CLARIFICATION_NEEDED
  INTAKE_DONE         -> PlannerAgent      -> PLAN_READY
  PLAN_READY          -> HumanPlanGate     -> AWAITING_HUMAN_PLAN (exits; human must approve)
  AWAITING_HUMAN_PLAN -> (check gate)      -> PLAN_APPROVED | PLAN_REJECTED
  PLAN_APPROVED       -> CoderAgent        -> CODE_DONE
  CODE_DONE           -> TestAnalystAgent  -> TEST_ANALYSIS_DONE
  TEST_ANALYSIS_DONE  -> VerificationGate  -> VERIFIED | VERIFICATION_FAILED
  VERIFIED            -> (write evidence)  -> SLICE_COMPLETE
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"

# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _state_path(change_id: str) -> Path:
    return RUNS / change_id / "factory-state.json"


def load_state(change_id: str) -> dict:
    path = _state_path(change_id)
    if not path.exists():
        raise SystemExit(
            f"Run '{change_id}' not found. Run: python scripts/start_run.py {change_id}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(change_id: str, state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    _state_path(change_id).write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_evidence(change_id: str, filename: str, content: str) -> Path:
    """Write a file to runs/<change_id>/ and return the path."""
    folder = RUNS / change_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# ADK runner helper
# ---------------------------------------------------------------------------

async def _invoke_agent(agent, input_text: str, session_state: dict) -> str:
    """Run a single ADK LlmAgent and return its output_key value."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    app_name = "factory_app"
    user_id = "factory-runner"
    session_id = f"run-{session_state.get('change_id', 'unknown')}-{agent.name}"

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=dict(session_state),  # inject current pipeline state
    )

    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)

    events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=input_text)]),
    )

    async for _ in events:
        pass  # consume; output is stored in session.state[output_key]

    final_session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    output_key = agent.output_key
    return final_session.state.get(output_key, "")


def run_agent(agent, input_text: str, session_state: dict) -> str:
    return asyncio.run(_invoke_agent(agent, input_text, session_state))


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_intake(change_id: str, state: dict) -> dict:
    print("\n[STAGE 1/6] IntakeAgent — analysing change request...")
    from factory_app.agents import intake_agent

    cr_path = RUNS / change_id / "00-change-request.md"
    if not cr_path.exists():
        # Fallback: search change_requests/
        matches = sorted((ROOT / "change_requests").glob(f"{change_id}-*.md"))
        if not matches:
            raise SystemExit(f"Change request for {change_id} not found.")
        cr_path = matches[0]

    cr_text = cr_path.read_text(encoding="utf-8")
    state["cr_text"] = cr_text

    prompt = (
        f"Change ID: {change_id}\n\n"
        f"Change Request text:\n{cr_text}\n\n"
        "Produce the intake report now."
    )
    output = run_agent(intake_agent, prompt, state)
    state["intake_report"] = output

    p = write_evidence(change_id, "01-intake-report.md", output)
    print(f"  -> Intake report written: {p.relative_to(ROOT)}")

    if "HUMAN_CLARIFICATION_REQUIRED" in output.upper():
        print("\n  ⚠  IntakeAgent requires human clarification. Run stopped.")
        state["status"] = "CLARIFICATION_NEEDED"
    else:
        state["status"] = "INTAKE_DONE"

    save_state(change_id, state)
    return state


def stage_planner(change_id: str, state: dict) -> dict:
    print("\n[STAGE 2/6] PlannerAgent — producing implementation plan...")
    from factory_app.agents import planner_agent

    prompt = (
        f"Change ID: {change_id}\n\n"
        "Intake report is in context. Produce the full implementation plan now."
    )
    output = run_agent(planner_agent, prompt, state)
    state["implementation_plan"] = output

    p = write_evidence(change_id, "02-implementation-plan.md", output)
    print(f"  -> Plan written: {p.relative_to(ROOT)}")
    state["status"] = "PLAN_READY"
    save_state(change_id, state)
    return state


def stage_human_plan_gate(change_id: str, state: dict) -> dict:
    print("\n[STAGE 3/6] Human Plan Gate — pipeline suspended.")
    print(f"\n  Review the plan at: runs/{change_id}/02-implementation-plan.md")
    print("\n  Then run one of:")
    print(f'    python scripts/approve_gate.py {change_id} plan APPROVED "your reason"')
    print(f'    python scripts/approve_gate.py {change_id} plan REJECTED "your reason"')
    print("\n  Then re-run:  python scripts/run_factory.py", change_id)
    state["status"] = "AWAITING_HUMAN_PLAN"
    save_state(change_id, state)
    return state


def stage_check_plan_decision(change_id: str, state: dict) -> dict:
    """Read the human gate decision and advance status accordingly."""
    decision_path = RUNS / change_id / "human-plan-decision.json"
    if not decision_path.exists():
        print(
            f"\n  Waiting for human plan decision.\n"
            f"  Run: python scripts/approve_gate.py {change_id} plan APPROVED \"reason\""
        )
        sys.exit(0)

    decision_data = json.loads(decision_path.read_text(encoding="utf-8"))
    decision = decision_data.get("decision", "").upper()
    state["human_plan_decision"] = decision
    state["human_plan_reason"] = decision_data.get("reason", "")

    if decision == "APPROVED":
        print(f"\n  ✅ Plan APPROVED by human: {decision_data.get('reason', '')}")
        state["status"] = "PLAN_APPROVED"
    else:
        print(f"\n  ❌ Plan {decision}: {decision_data.get('reason', '')}. Pipeline stopped.")
        state["status"] = "PLAN_REJECTED"

    save_state(change_id, state)
    return state


def stage_coder(change_id: str, state: dict) -> dict:
    print("\n[STAGE 4/6] CoderAgent — implementing approved plan...")
    from factory_app.agents import coder_agent

    prompt = (
        f"Change ID: {change_id}\n"
        f"Human decision: {state.get('human_plan_decision', 'APPROVED')}\n\n"
        "The plan above has been approved by a human. Implement it now using "
        "write_product_file. After writing all files, produce your coder_report."
    )
    output = run_agent(coder_agent, prompt, state)
    state["coder_report"] = output

    p = write_evidence(change_id, "03-coder-report.md", output)
    print(f"  -> Coder report written: {p.relative_to(ROOT)}")
    state["status"] = "CODE_DONE"
    save_state(change_id, state)
    return state


def stage_test_analyst(change_id: str, state: dict) -> dict:
    print("\n[STAGE 5/6] TestAnalystAgent — analysing and writing tests...")
    from factory_app.agents import test_analyst_agent

    prompt = (
        f"Change ID: {change_id}\n\n"
        "The coder report is in context. Run baseline verification, analyse coverage "
        "against every AC in the CR, write any missing tests using write_test_file, "
        "then produce the test_analysis report."
    )
    output = run_agent(test_analyst_agent, prompt, state)
    state["test_analysis"] = output

    p = write_evidence(change_id, "04-test-analysis.md", output)
    print(f"  -> Test analysis written: {p.relative_to(ROOT)}")
    state["status"] = "TEST_ANALYSIS_DONE"
    save_state(change_id, state)
    return state


def stage_verification_gate(change_id: str, state: dict) -> dict:
    """Deterministic gate — no LLM involved."""
    print("\n[STAGE 6/6] VerificationGate — running pytest + ruff (deterministic)...")
    # Import directly; no LLM.
    import subprocess

    commands = [
        ["python", "-m", "pytest", "-v", "--tb=short"],
        ["python", "-m", "ruff", "check", "campusflow", "tests", "factory_app", "scripts"],
    ]
    all_ok = True
    results = []
    for cmd in commands:
        completed = subprocess.run(
            cmd, cwd=ROOT, text=True, capture_output=True, timeout=120, check=False
        )
        ok = completed.returncode == 0
        all_ok = all_ok and ok
        results.append({
            "command": " ".join(cmd),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-3000:],
            "passed": ok,
        })
        status_icon = "✅" if ok else "❌"
        print(f"  {status_icon} {' '.join(cmd)}  (exit {completed.returncode})")

    verification_evidence = {
        "change_id": change_id,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": all_ok,
        "results": results,
    }
    p = write_evidence(
        change_id,
        "05-verification.json",
        json.dumps(verification_evidence, indent=2),
    )
    print(f"  -> Verification evidence written: {p.relative_to(ROOT)}")

    state["verification_result"] = verification_evidence
    if all_ok:
        print("\n  ✅ All checks passed.")
        state["status"] = "VERIFIED"
    else:
        print("\n  ❌ Verification FAILED — pipeline halted. Fix failures and re-run.")
        state["status"] = "VERIFICATION_FAILED"

    save_state(change_id, state)
    return state


def stage_write_slice_evidence(change_id: str, state: dict) -> dict:
    """Write a final traceability summary for the slice."""
    print("\n  Writing slice summary evidence...")
    summary = {
        "change_id": change_id,
        "slice": (
            "Change Request -> Intake -> Planner -> "
            "Human Approval -> Coder -> Test Analyst -> Verification"
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "stages": {
            "intake": "DONE",
            "planning": "DONE",
            "human_plan_gate": state.get("human_plan_decision", "APPROVED"),
            "coder": "DONE",
            "test_analyst": "DONE",
            "verification": "PASSED",
        },
        "human_plan_reason": state.get("human_plan_reason", ""),
        "note": "M3 (Review/Security) and M4 (Fix/Release) are out of scope for this slice.",
    }
    p = write_evidence(change_id, "06-slice-summary.json", json.dumps(summary, indent=2))
    print(f"  -> Slice summary written: {p.relative_to(ROOT)}")
    state["status"] = "SLICE_COMPLETE"
    save_state(change_id, state)
    return state


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

STATUS_DISPATCH = {
    "INTAKE_PENDING":       stage_intake,
    "INTAKE_DONE":          stage_planner,
    "PLAN_READY":           stage_human_plan_gate,
    "AWAITING_HUMAN_PLAN":  stage_check_plan_decision,
    "PLAN_APPROVED":        stage_coder,
    "CODE_DONE":            stage_test_analyst,
    "TEST_ANALYSIS_DONE":   stage_verification_gate,
    "VERIFIED":             stage_write_slice_evidence,
}

TERMINAL_STATUSES = {
    "SLICE_COMPLETE",
    "VERIFICATION_FAILED",
    "PLAN_REJECTED",
    "CLARIFICATION_NEEDED",
}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/run_factory.py CR-001")
    change_id = sys.argv[1].strip().upper()

    print(f"\n{'='*60}")
    print(f"  Agentic Software Factory — {change_id}")
    print(f"{'='*60}")

    # Pipeline loop: advance as many stages as possible in one invocation.
    while True:
        state = load_state(change_id)
        status = state.get("status", "INTAKE_PENDING")

        print(f"\nCurrent status: {status}")

        if status in TERMINAL_STATUSES:
            print(f"\n  Pipeline is in terminal state '{status}'. Nothing more to run.")
            if status == "SLICE_COMPLETE":
                print(f"  🎉 Slice complete! Evidence in runs/{change_id}/")
            break

        handler = STATUS_DISPATCH.get(status)
        if handler is None:
            raise SystemExit(f"Unknown pipeline status: {status!r}")

        state = handler(change_id, state)

        # Re-read status after handler (handler updates and saves state)
        new_status = state.get("status", "")

        # Stop advancing if we're waiting for human input or hit a terminal state
        if new_status in TERMINAL_STATUSES or new_status == "AWAITING_HUMAN_PLAN":
            break

        # Prevent infinite loop on unexpected same-status
        if new_status == status:
            print(f"\n  Warning: status did not advance from {status!r}. Stopping.")
            break


if __name__ == "__main__":
    main()
