from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_coder_blocked_when_plan_not_approved():
    test_cr = "CR-TEST-CODER-GATE"
    run_dir = ROOT / "runs" / test_cr
    if run_dir.exists():
        shutil.rmtree(run_dir)

    run_dir.mkdir(parents=True)
    (run_dir / "00-change-request.md").write_text("# CR-TEST\nTest", encoding="utf-8")
    (run_dir / "02-implementation-plan.md").write_text("# Plan", encoding="utf-8")
    initial_state = {
        "change_id": test_cr,
        "status": "PLAN_REVIEW_PENDING",
        "human_gates": {
            "requirements": "ACCEPTED",
            "plan": "PENDING",
            "review": "PENDING",
            "release": "PENDING",
        },
    }
    (run_dir / "factory-state.json").write_text(json.dumps(initial_state), encoding="utf-8")

    try:
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_coder.py"),
            test_cr,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "GATE BLOCKED" in res.stdout or "GATE BLOCKED" in res.stderr
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
