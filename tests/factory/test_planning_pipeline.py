from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_start_run_and_state_lifecycle(tmp_path):
    test_cr = "CR-TEST-999"
    run_dir = ROOT / "runs" / test_cr
    if run_dir.exists():
        shutil.rmtree(run_dir)

    run_dir.mkdir(parents=True)
    (run_dir / "00-change-request.md").write_text("# CR-TEST-999\nTest", encoding="utf-8")
    initial_state = {
        "change_id": test_cr,
        "status": "INTAKE_PENDING",
        "human_gates": {
            "requirements": "PENDING",
            "plan": "PENDING",
            "review": "PENDING",
            "release": "PENDING",
        },
    }
    (run_dir / "factory-state.json").write_text(json.dumps(initial_state), encoding="utf-8")

    try:
        # 1. Plan cannot be approved if 02-implementation-plan.md does not exist
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "approve_gate.py"),
            test_cr,
            "plan",
            "APPROVED",
            "test reason",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "Cannot approve plan" in res.stderr or "Cannot approve plan" in res.stdout

        # 2. Simulate planner generating the plan
        (run_dir / "02-implementation-plan.md").write_text("# Plan", encoding="utf-8")

        # 3. Now plan approval should succeed
        cmd[5] = "Approved plan"
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0

        # Verify state updated
        state = json.loads((run_dir / "factory-state.json").read_text(encoding="utf-8"))
        assert state["status"] == "PLAN_APPROVED"
        assert state["human_gates"]["plan"] == "APPROVED"

        # Verify evidence recorded
        evidence = json.loads((run_dir / "human-plan-decision.json").read_text(encoding="utf-8"))
        assert evidence["decision"] == "APPROVED"
        assert evidence["reason"] == "Approved plan"
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
