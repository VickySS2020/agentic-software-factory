from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    [sys.executable, "-m", "pytest", "-q"],
    [sys.executable, "-m", "ruff", "check", "campusflow", "tests", "factory_app", "scripts"],
]


def main() -> int:
    failed = False
    for command in COMMANDS:
        print(f"\n$ {' '.join(command)}")
        result = subprocess.run(command, cwd=ROOT, check=False)
        failed = failed or result.returncode != 0
    print("\nVERIFY_REPO:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
