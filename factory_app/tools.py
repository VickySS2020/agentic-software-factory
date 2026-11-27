from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
READABLE_ROOTS = {"docs", "change_requests", "campusflow", "tests", "runs"}
WRITABLE_CODE_ROOTS = {"campusflow", "src", "tests"}
WRITABLE_TEST_ROOTS = {"tests"}


def _safe_repo_path(relative_path: str) -> Path:
    candidate = (REPO_ROOT / relative_path).resolve()
    if REPO_ROOT not in candidate.parents and candidate != REPO_ROOT:
        raise ValueError("path escapes repository")
    return candidate


def list_repo_files(prefix: str = "") -> dict:
    """List files under an allowlisted read-only area."""
    prefix = prefix.strip().strip("/")
    if prefix:
        top = prefix.split("/", 1)[0]
        if top not in READABLE_ROOTS:
            return {"ok": False, "error": f"read not allowed under {top!r}"}
        root = _safe_repo_path(prefix)
    else:
        root = REPO_ROOT
    if not root.exists():
        return {"ok": False, "error": "path does not exist"}
    items = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT)
        if not prefix and rel.parts[0] not in READABLE_ROOTS:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        items.append(str(rel))
    return {"ok": True, "files": items[:250]}


def read_repo_file(relative_path: str) -> dict:
    """Read UTF-8 text from an allowlisted repository area."""
    path = _safe_repo_path(relative_path)
    rel = path.relative_to(REPO_ROOT)
    if not rel.parts or rel.parts[0] not in READABLE_ROOTS:
        return {"ok": False, "error": "read not allowed for this path"}
    if not path.is_file():
        return {"ok": False, "error": "file does not exist"}
    if path.suffix.lower() in {".db", ".png", ".jpg", ".jpeg", ".zip", ".pdf"}:
        return {"ok": False, "error": "binary file not supported"}
    text = path.read_text(encoding="utf-8")
    if len(text) > 40_000:
        text = text[:40_000] + "\n...[TRUNCATED]..."
    return {"ok": True, "path": str(rel), "content": text}


def run_baseline_verification() -> dict:
    """Run an allowlisted deterministic baseline. No arbitrary shell input."""
    commands = [
        ["python", "-m", "pytest", "-q"],
        ["python", "-m", "ruff", "check", "campusflow", "tests", "factory_app", "scripts"],
    ]
    results = []
    all_ok = True
    for command in commands:
        completed = subprocess.run(
            command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=120, check=False
        )
        all_ok = all_ok and completed.returncode == 0
        results.append({
            "command": " ".join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-6000:],
            "stderr": completed.stderr[-3000:],
        })
    return {"ok": all_ok, "results": results}


def write_run_evidence(change_id: str, filename: str, content: str) -> dict:
    """Write only evidence files under runs/<CR-ID>/; never product code."""
    if not change_id.startswith("CR-"):
        return {"ok": False, "error": "change_id must start with CR-"}
    if "/" in filename or "\\" in filename or not filename.endswith((".md", ".json", ".txt")):
        return {"ok": False, "error": "invalid evidence filename"}
    folder = REPO_ROOT / "runs" / change_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(path.relative_to(REPO_ROOT))}


def write_code_file(relative_path: str, content: str) -> dict:
    """Write UTF-8 text to an allowlisted code or test directory (campusflow, src, tests).

    Prevents modifying docs, change_requests, factory_app, scripts, or root files.
    """
    path = _safe_repo_path(relative_path)
    rel = path.relative_to(REPO_ROOT)
    if not rel.parts or rel.parts[0] not in WRITABLE_CODE_ROOTS:
        allowed = sorted(WRITABLE_CODE_ROOTS)
        return {"ok": False, "error": f"Write not allowed for {rel}. Allowed roots: {allowed}"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(rel)}


def run_limited_command(command: str) -> dict:
    """Execute allowlisted test and lint commands only (pytest, ruff).

    Rejects arbitrary shell commands, pipe/chain operators, or network tools.
    """
    tokens = shlex.split(command)
    if not tokens:
        return {"ok": False, "error": "empty command"}

    base_cmd = Path(tokens[0]).stem.lower()
    cmd_to_run: list[str]

    if base_cmd in {"pytest", "ruff"}:
        cmd_to_run = [sys.executable, "-m", base_cmd] + tokens[1:]
    elif base_cmd in {"python", "python3"} and len(tokens) >= 3:
        if tokens[1] == "-m" and tokens[2] in {"pytest", "ruff"}:
            cmd_to_run = [sys.executable] + tokens[1:]
        else:
            return {
                "ok": False,
                "error": (
                    f"Command not allowed: {command}. Only pytest and ruff modules are permitted."
                ),
            }
    else:
        return {
            "ok": False,
            "error": f"Command not allowed: {tokens[0]}. Only pytest and ruff are permitted.",
        }

    completed = subprocess.run(
        cmd_to_run,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-3000:],
    }


def write_coder_report(change_id: str, content: str) -> dict:
    """Save coder-report.md (and 04-coder-report.md) in the run evidence folder."""
    res = write_run_evidence(change_id, "coder-report.md", content)
    if res.get("ok"):
        write_run_evidence(change_id, "04-coder-report.md", content)
    return res


def write_test_file(relative_path: str, content: str) -> dict:
    """Write UTF-8 text strictly to the tests/ directory.

    Prevents modifying application code (campusflow/, src/), docs, change_requests,
    factory_app, scripts, or root files.
    """
    path = _safe_repo_path(relative_path)
    rel = path.relative_to(REPO_ROOT)
    if not rel.parts or rel.parts[0] not in WRITABLE_TEST_ROOTS:
        return {
            "ok": False,
            "error": f"Write not allowed for {rel}. Test Analyst may only write to 'tests/'.",
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(rel)}


def get_coder_diff(change_id: str = "") -> dict:
    """Retrieve git diff of code changes introduced for the change request."""
    diff_output = ""
    if change_id:
        target_branch = f"cr/{change_id}"
        res = subprocess.run(
            ["git", "diff", f"main...{target_branch}"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            diff_output = res.stdout

    if not diff_output:
        res = subprocess.run(
            ["git", "diff", "HEAD~1"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            diff_output = res.stdout

    if not diff_output:
        res = subprocess.run(
            ["git", "diff"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            diff_output = res.stdout

    if len(diff_output) > 40_000:
        diff_output = diff_output[:40_000] + "\n...[TRUNCATED]..."

    return {"ok": True, "diff": diff_output}


def write_test_analysis_report(change_id: str, content: str) -> dict:
    """Save 05-test-analysis.md (and test-analysis.md) in the run evidence folder."""
    res = write_run_evidence(change_id, "05-test-analysis.md", content)
    if res.get("ok"):
        write_run_evidence(change_id, "test-analysis.md", content)
    return res


def write_verification_report(change_id: str, content: str) -> dict:
    """Save 06-verification.md (and verification.md) in the run evidence folder."""
    res = write_run_evidence(change_id, "06-verification.md", content)
    if res.get("ok"):
        write_run_evidence(change_id, "verification.md", content)
    return res
