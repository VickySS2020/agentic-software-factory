from __future__ import annotations

import shutil

from factory_app.tools import (
    REPO_ROOT,
    get_coder_diff,
    write_test_analysis_report,
    write_test_file,
)


def test_write_test_file_permissions():
    # Allowed area: tests/
    test_target = "tests/test_dummy_analyst_scratch.py"
    try:
        res = write_test_file(test_target, "# dummy test analyst\n")
        assert res["ok"] is True
        assert (REPO_ROOT / test_target).exists()
    finally:
        target_path = REPO_ROOT / test_target
        if target_path.exists():
            target_path.unlink()

    # Blocked areas: campusflow (APPLICATION CODE), src, docs, factory_app,
    # change_requests, scripts, root
    blocked_targets = [
        "campusflow/service.py",
        "campusflow/malicious.py",
        "src/app.py",
        "docs/LEAK.md",
        "factory_app/tools.py",
        "change_requests/CR-999.md",
        "scripts/bad.py",
        "README.md",
        "../outside.txt",
    ]
    for target in blocked_targets:
        try:
            res = write_test_file(target, "should fail")
            assert res["ok"] is False
            assert "not allowed" in res["error"].lower()
        except ValueError:
            # Traversal attempt properly caught by _safe_repo_path
            pass


def test_write_test_analysis_report():
    test_cr = "CR-TEST-ANALYST"
    run_dir = REPO_ROOT / "runs" / test_cr
    try:
        res = write_test_analysis_report(test_cr, "# Test Analysis Report\n")
        assert res["ok"] is True
        assert (run_dir / "05-test-analysis.md").exists()
        assert (run_dir / "test-analysis.md").exists()
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


def test_get_coder_diff_returns_dict():
    res = get_coder_diff()
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert "diff" in res
