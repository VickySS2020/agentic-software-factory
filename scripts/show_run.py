import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/show_run.py CR-001")
path = ROOT / "runs" / sys.argv[1].upper() / "factory-state.json"
if not path.exists():
    raise SystemExit("Run not found")
print(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))
