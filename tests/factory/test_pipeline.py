"""Factory pipeline contract tests.

Covers:
- Tool boundary enforcement (write_product_file, write_test_file)
- Gate state machine transitions (approve_gate.py logic)
- run_factory.py state helpers
- Evidence file naming rules (write_run_evidence)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Tool boundary tests — write_product_file
# ---------------------------------------------------------------------------

class TestWriteProductFile:
    """write_product_file must only write under campusflow/."""

    def _tool(self, tmp_path: Path):
        """Return a patched version of write_product_file using tmp_path as repo root."""
        import factory_app.tools as tools_mod
        original_root = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        # Create campusflow/ so writes can succeed.
        (tmp_path / "campusflow").mkdir(parents=True, exist_ok=True)
        yield tools_mod.write_product_file
        tools_mod.REPO_ROOT = original_root

    def test_allows_campusflow_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        (tmp_path / "campusflow").mkdir(parents=True, exist_ok=True)
        try:
            result = tools_mod.write_product_file("campusflow/service.py", "# test")
            assert result["ok"] is True
            assert (tmp_path / "campusflow" / "service.py").read_text() == "# test"
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_docs_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_product_file("docs/REQUIREMENTS.md", "# hack")
            assert result["ok"] is False
            assert "campusflow" in result["error"]
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_tests_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_product_file("tests/product/test_x.py", "# hack")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_path_traversal(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_product_file("campusflow/../../etc/passwd", "hack")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_non_py_extension(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_product_file("campusflow/secret.sh", "rm -rf /")
            assert result["ok"] is False
            assert "only" in result["error"]
        finally:
            tools_mod.REPO_ROOT = original


# ---------------------------------------------------------------------------
# Tool boundary tests — write_test_file
# ---------------------------------------------------------------------------

class TestWriteTestFile:
    """write_test_file must only write under tests/product/ or tests/factory/."""

    def test_allows_product_test_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        (tmp_path / "tests" / "product").mkdir(parents=True, exist_ok=True)
        try:
            result = tools_mod.write_test_file("tests/product/test_waitlist.py", "# new test")
            assert result["ok"] is True
        finally:
            tools_mod.REPO_ROOT = original

    def test_allows_factory_test_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        (tmp_path / "tests" / "factory").mkdir(parents=True, exist_ok=True)
        try:
            result = tools_mod.write_test_file("tests/factory/test_new_case.py", "# new test")
            assert result["ok"] is True
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_campusflow_path(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_test_file("campusflow/test_hack.py", "# hack")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_non_test_prefix_filename(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_test_file("tests/product/helper.py", "# not a test")
            assert result["ok"] is False
            assert "test_" in result["error"]
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_path_traversal(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_test_file("tests/product/../../campusflow/test_x.py", "x")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original


# ---------------------------------------------------------------------------
# write_run_evidence boundary tests
# ---------------------------------------------------------------------------

class TestWriteRunEvidence:
    def test_requires_cr_prefix(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_run_evidence("EVIL-001", "report.md", "x")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_path_separator_in_filename(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_run_evidence("CR-001", "../escape.md", "x")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_rejects_disallowed_extension(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_run_evidence("CR-001", "report.sh", "x")
            assert result["ok"] is False
        finally:
            tools_mod.REPO_ROOT = original

    def test_writes_valid_evidence(self, tmp_path):
        import factory_app.tools as tools_mod
        original = tools_mod.REPO_ROOT
        tools_mod.REPO_ROOT = tmp_path
        try:
            result = tools_mod.write_run_evidence("CR-001", "report.md", "evidence content")
            assert result["ok"] is True
            assert (tmp_path / "runs" / "CR-001" / "report.md").read_text() == "evidence content"
        finally:
            tools_mod.REPO_ROOT = original


# ---------------------------------------------------------------------------
# approve_gate.py state transition tests
# ---------------------------------------------------------------------------

class TestApproveGate:
    """approve_gate.py must write correct pipeline status transitions."""

    def _make_run(self, tmp_path: Path, change_id: str = "CR-001") -> Path:
        run = tmp_path / "runs" / change_id
        run.mkdir(parents=True)
        state = {
            "change_id": change_id,
            "status": "AWAITING_HUMAN_PLAN",
            "human_gates": {
                "requirements": "PENDING",
                "plan": "PENDING",
                "review": "PENDING",
                "release": "PENDING",
            },
        }
        (run / "factory-state.json").write_text(json.dumps(state), encoding="utf-8")
        return run

    def test_plan_approved_advances_status(self, tmp_path, monkeypatch):
        import scripts.approve_gate as ag
        monkeypatch.setattr(ag, "ROOT", tmp_path)
        run = self._make_run(tmp_path)

        # Simulate CLI args
        import sys
        monkeypatch.setattr(
            sys,
            "argv",
            ["approve_gate.py", "CR-001", "plan", "APPROVED", "looks good"],
        )
        ag.main()

        state = json.loads((run / "factory-state.json").read_text())
        assert state["status"] == "PLAN_APPROVED"
        assert state["human_gates"]["plan"] == "APPROVED"
        assert (run / "human-plan-decision.json").exists()

    def test_plan_rejected_advances_status(self, tmp_path, monkeypatch):
        import scripts.approve_gate as ag
        monkeypatch.setattr(ag, "ROOT", tmp_path)
        self._make_run(tmp_path)

        import sys
        monkeypatch.setattr(
            sys,
            "argv",
            ["approve_gate.py", "CR-001", "plan", "REJECTED", "needs rework"],
        )
        ag.main()

        state = json.loads((tmp_path / "runs" / "CR-001" / "factory-state.json").read_text())
        assert state["status"] == "PLAN_REJECTED"

    def test_requires_reason(self, tmp_path, monkeypatch):
        import scripts.approve_gate as ag
        monkeypatch.setattr(ag, "ROOT", tmp_path)
        self._make_run(tmp_path)

        import sys
        monkeypatch.setattr(sys, "argv", ["approve_gate.py", "CR-001", "plan", "APPROVED", ""])
        with pytest.raises(SystemExit):
            ag.main()

    def test_rejects_invalid_gate(self, tmp_path, monkeypatch):
        import scripts.approve_gate as ag
        monkeypatch.setattr(ag, "ROOT", tmp_path)
        self._make_run(tmp_path)

        import sys
        monkeypatch.setattr(sys, "argv", ["approve_gate.py", "CR-001", "badgate", "APPROVED", "r"])
        with pytest.raises(SystemExit):
            ag.main()

    def test_rejects_invalid_decision(self, tmp_path, monkeypatch):
        import scripts.approve_gate as ag
        monkeypatch.setattr(ag, "ROOT", tmp_path)
        self._make_run(tmp_path)

        import sys
        monkeypatch.setattr(sys, "argv", ["approve_gate.py", "CR-001", "plan", "YOLO", "r"])
        with pytest.raises(SystemExit):
            ag.main()


# ---------------------------------------------------------------------------
# run_factory.py state helpers
# ---------------------------------------------------------------------------

class TestRunFactoryStateHelpers:
    def test_load_state_raises_when_missing(self, tmp_path, monkeypatch):
        import scripts.run_factory as rf
        monkeypatch.setattr(rf, "RUNS", tmp_path / "runs")
        with pytest.raises(SystemExit):
            rf.load_state("CR-001")

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        import scripts.run_factory as rf
        runs = tmp_path / "runs"
        runs.mkdir()
        monkeypatch.setattr(rf, "RUNS", runs)
        (runs / "CR-001").mkdir()
        state = {"change_id": "CR-001", "status": "INTAKE_PENDING"}
        rf.save_state("CR-001", state)
        loaded = rf.load_state("CR-001")
        assert loaded["status"] == "INTAKE_PENDING"
        assert "updated_at" in loaded  # save_state must stamp updated_at

    def test_write_evidence_creates_file(self, tmp_path, monkeypatch):
        import scripts.run_factory as rf
        runs = tmp_path / "runs"
        runs.mkdir()
        monkeypatch.setattr(rf, "RUNS", runs)
        p = rf.write_evidence("CR-001", "test.md", "hello")
        assert p.read_text() == "hello"
