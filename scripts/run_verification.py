from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factory_app.tools import write_verification_report  # noqa: E402
from scripts.run_coder import run_coder_fix  # noqa: E402

RUNS = ROOT / "runs"
MAX_FIX_ITERATIONS = 5

VERIFICATION_COMMANDS = [
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "-m", "ruff", "check", "campusflow", "tests", "factory_app", "scripts"],
]


def update_state(run_dir: Path, **updates) -> dict:
    state_file = run_dir / "factory-state.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state.update(updates)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def execute_deterministic_checks() -> tuple[bool, list[dict]]:
    results = []
    all_ok = True
    for command in VERIFICATION_COMMANDS:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        passed = completed.returncode == 0
        all_ok = all_ok and passed
        results.append({
            "command": " ".join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:],
            "passed": passed,
        })
    return all_ok, results


def format_verification_report(
    change_id: str, passed: bool, iteration: int, results: list[dict]
) -> str:
    verdict = "PASS" if passed else "FAIL"
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Verification Report — {change_id}",
        "",
        f"- **Verdict**: `{verdict}`",
        f"- **Iteration**: {iteration}",
        f"- **Timestamp**: `{now}`",
        "",
        "## Deterministic Check Results",
        "",
    ]
    for res in results:
        status_badge = "PASSED" if res["passed"] else "FAILED"
        lines.append(
            f"### Command: `{res['command']}` — **{status_badge}** (exit code {res['returncode']})"
        )
        lines.append("")
        if res["stdout"].strip():
            lines.append("```text")
            lines.append(res["stdout"].strip())
            lines.append("```")
            lines.append("")
        if res["stderr"].strip():
            lines.append("**stderr:**")
            lines.append("```text")
            lines.append(res["stderr"].strip())
            lines.append("```")
            lines.append("")

    lines.append("## Gate Status")
    lines.append("")
    if passed:
        lines.append(
            "Verification passed all deterministic checks. "
            "Change is eligible for Reviewer and Security."
        )
    else:
        lines.append(
            "Verification FAILED. Change cannot proceed to Reviewer or Security; "
            "returning to Coder/Fix."
        )
    lines.append("")
    return "\n".join(lines)


def run_verification(change_id: str, auto_fix: bool = True) -> int:
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

    allowed_prereqs = {
        "TEST_ANALYSIS_COMPLETED",
        "CODING_COMPLETED",
        "FIX_COMPLETED",
        "VERIFICATION_FAILED",
        "VERIFICATION_RUNNING",
    }
    if status not in allowed_prereqs and state.get("verification") == "NOT_RUN":
        print(f"\n[GATE BLOCKED] Prerequisites not met for verification. Current status: {status}")
        print("Test Analyst or Coder stage must complete first.")
        return 1

    iteration = state.get("iterations", 0)

    while True:
        iteration += 1
        print(f"\n=== Running Verification Gate for {change_id} (Iteration {iteration}) ===")
        update_state(run_dir, status="VERIFICATION_RUNNING", iterations=iteration)

        all_ok, results = execute_deterministic_checks()
        verdict = "PASS" if all_ok else "FAIL"

        # Generate and save 06-verification.md regardless of PASS or FAIL
        report_content = format_verification_report(change_id, all_ok, iteration, results)
        write_verification_report(change_id, report_content)

        # Update verification state in factory-state.json
        state_status = "VERIFICATION_PASSED" if all_ok else "VERIFICATION_FAILED"
        update_state(
            run_dir,
            verification=verdict,
            status=state_status,
            iterations=iteration,
        )

        verif_doc = run_dir / "06-verification.md"
        rel_path = verif_doc.relative_to(ROOT)
        print(f"Verification output saved -> {rel_path} (Verdict: {verdict})")

        if all_ok:
            print(f"\n[GATE PASSED] Verification passed for {change_id} (Iteration {iteration}).")
            print("Deterministic checks verified. Ready for Independent Reviewer & Security.")
            return 0

        print(f"\n[GATE FAILED] Verification failed on iteration {iteration}.")
        if not auto_fix:
            print("Auto-fix disabled. Change halts at Verification Gate.")
            return 1

        if iteration >= MAX_FIX_ITERATIONS:
            print(f"\n[STOP CONDITION] Reached maximum fix iterations ({MAX_FIX_ITERATIONS}).")
            print("Halting for human review and intervention.")
            update_state(run_dir, status="VERIFICATION_MAX_ITERATIONS_STOP")
            return 1

        # Failure triggers Coder Fix Loop
        print(f"\n[CODER FIX LOOP] Returning to Coder to fix mistakes (Iteration {iteration})...")
        fix_code = run_coder_fix(change_id, report_content)
        if fix_code != 0:
            print(f"Coder fix execution failed with code {fix_code}.")
            return fix_code


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/run_verification.py CR-001 [--no-fix]")
    change_id = sys.argv[1].strip().upper()
    auto_fix = "--no-fix" not in sys.argv
    exit_code = run_verification(change_id, auto_fix=auto_fix)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
