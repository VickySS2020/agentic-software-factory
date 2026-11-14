from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CR_DIR = ROOT / "change_requests"
RUNS = ROOT / "runs"


def find_change_request(change_id: str) -> Path:
    matches = sorted(CR_DIR.glob(f"{change_id}-*.md"))
    if len(matches) != 1:
        raise SystemExit(f"Expected one Change Request for {change_id}; found {len(matches)}")
    return matches[0]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/start_run.py CR-001")
    change_id = sys.argv[1].strip().upper()
    source = find_change_request(change_id)
    run = RUNS / change_id
    if run.exists():
        raise SystemExit(f"Run already exists: {run}")
    run.mkdir(parents=True)
    shutil.copy2(source, run / "00-change-request.md")
    state = {
        "change_id": change_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "INTAKE_PENDING",
        "human_gates": {
            "requirements": "PENDING",
            "plan": "PENDING",
            "review": "PENDING",
            "release": "PENDING",
        },
        "verification": "NOT_RUN",
        "review": "NOT_RUN",
        "security": "NOT_RUN",
        "iterations": 0,
    }
    (run / "factory-state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Created {run.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
