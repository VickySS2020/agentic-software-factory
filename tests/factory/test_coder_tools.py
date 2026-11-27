from __future__ import annotations

import shutil

from factory_app.tools import (
    REPO_ROOT,
    run_limited_command,
    write_code_file,
    write_coder_report,
)


def test_write_code_file_permissions(tmp_path):
    # Allowed areas: campusflow, tests
    test_target = "tests/test_dummy_scratch.py"
    try:
        res = write_code_file(test_target, "# scratch test\n")
        assert res["ok"] is True
        assert (REPO_ROOT / test_target).exists()
    finally:
        target_path = REPO_ROOT / test_target
        if target_path.exists():
            target_path.unlink()

    # Blocked areas: docs, factory_app, change_requests, scripts, root
    blocked_targets = [
        "docs/LEAK.md",
        "factory_app/malicious.py",
        "change_requests/CR-999.md",
        "scripts/bad.py",
        "README.md",
        "../outside.txt",
    ]
    for target in blocked_targets:
        try:
            res = write_code_file(target, "should fail")
            assert res["ok"] is False
        except ValueError:
            # Traversal attempt properly caught by _safe_repo_path
            pass


def test_run_limited_command_allowlist():
    # Allowlisted: pytest -h or --version
    res = run_limited_command("pytest --version")
    assert res["ok"] is True

    # Blocked commands
    blocked = [
        "ls",
        "dir",
        "cmd.exe /c whoami",
        "powershell Get-Process",
        "curl https://google.com",
    ]
    for cmd in blocked:
        res = run_limited_command(cmd)
        assert res["ok"] is False
        assert "not allowed" in res["error"].lower()


def test_write_coder_report():
    test_cr = "CR-TEST-CODER"
    run_dir = REPO_ROOT / "runs" / test_cr
    try:
        res = write_coder_report(test_cr, "# Coder Report Test\n")
        assert res["ok"] is True
        assert (run_dir / "coder-report.md").exists()
        assert (run_dir / "04-coder-report.md").exists()
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
