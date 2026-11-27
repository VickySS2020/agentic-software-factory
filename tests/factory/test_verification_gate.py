from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from factory_app.tools import write_verification_report
from scripts.run_verification import (
    format_verification_report,
)

ROOT = Path(__file__).resolve().parents[2]


def test_write_verification_report():
    test_cr = "CR-TEST-VERIF-DOC"
    run_dir = ROOT / "runs" / test_cr
    try:
        res = write_verification_report(test_cr, "# Test Verification Report\n")
        assert res["ok"] is True
        assert (run_dir / "06-verification.md").exists()
        assert (run_dir / "verification.md").exists()
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


def test_format_verification_report():
    results = [
        {
            "command": "python -m pytest -q",
            "returncode": 0,
            "stdout": "22 passed",
            "stderr": "",
            "passed": True,
        }
    ]
    report_pass = format_verification_report("CR-001", True, 1, results)
    assert "# Verification Report — CR-001" in report_pass
    assert "`PASS`" in report_pass
    assert "Verification passed all deterministic checks" in report_pass

    results_fail = [
        {
            "command": "python -m ruff check campusflow",
            "returncode": 1,
            "stdout": "1 error found",
            "stderr": "",
            "passed": False,
        }
    ]
    report_fail = format_verification_report("CR-001", False, 2, results_fail)
    assert "`FAIL`" in report_fail
    assert "Verification FAILED" in report_fail


def test_verification_blocked_when_prereqs_not_met():
    test_cr = "CR-TEST-VERIF-GATE"
    run_dir = ROOT / "runs" / test_cr
    if run_dir.exists():
        shutil.rmtree(run_dir)

    run_dir.mkdir(parents=True)
    initial_state = {
        "change_id": test_cr,
        "status": "PLAN_APPROVED",
        "human_gates": {"plan": "APPROVED"},
        "verification": "NOT_RUN",
        "iterations": 0,
    }
    (run_dir / "factory-state.json").write_text(json.dumps(initial_state), encoding="utf-8")

    try:
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_verification.py"),
            test_cr,
            "--no-fix",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "GATE BLOCKED" in res.stdout or "GATE BLOCKED" in res.stderr
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
