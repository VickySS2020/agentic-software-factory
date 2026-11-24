from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_GATES = {"requirements", "plan", "review", "release"}
VALID_DECISIONS = {"APPROVED", "MODIFIED", "REJECTED", "DEFERRED"}


def main() -> None:
    if len(sys.argv) < 5:
        raise SystemExit('Usage: python scripts/approve_gate.py CR-001 plan APPROVED "reason"')
    change_id = sys.argv[1].upper()
    gate = sys.argv[2].lower()
    decision = sys.argv[3].upper()
    reason = " ".join(sys.argv[4:]).strip()

    if gate not in VALID_GATES:
        raise SystemExit(f"Invalid gate: {sorted(VALID_GATES)}")
    if decision not in VALID_DECISIONS:
        raise SystemExit(f"Invalid decision: {sorted(VALID_DECISIONS)}")
    if not reason:
        raise SystemExit("Human decision requires a reason")

    run = ROOT / "runs" / change_id
    state_path = run / "factory-state.json"
    if not state_path.exists():
        raise SystemExit(f"Run not found: {change_id}")

    # Guard: Plan cannot be approved if the implementation plan file does not exist
    if gate == "plan" and decision == "APPROVED":
        plan_path = run / "02-implementation-plan.md"
        if not plan_path.exists():
            raise SystemExit(f"Cannot approve plan: {plan_path.name} has not been generated yet.")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["human_gates"][gate] = decision

    if gate == "plan":
        state["status"] = f"PLAN_{decision}"
    elif gate == "requirements":
        state["status"] = f"REQUIREMENTS_{decision}"

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    evidence = {
        "change_id": change_id,
        "gate": gate,
        "decision": decision,
        "reason": reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "recorded_by": os.environ.get("HUMAN_OPERATOR", "student/human-gatekeeper"),
    }
    path = run / f"human-{gate}-decision.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    if gate == "plan":
        plan_evidence = run / "03-human-plan-decision.json"
        plan_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"Recorded {gate}: {decision} -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
