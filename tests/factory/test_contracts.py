from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_required_repository_contract_files_exist():
    required = [
        "AGENTS.md",
        "docs/REQUIREMENTS.md",
        "docs/SPEC.md",
        "docs/ARCHITECTURE.md",
        "docs/REPO_MAP.md",
        "factory_app/agent.py",
        "factory_app/agents.py",
        "factory_app/tools.py",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"Missing contract files: {missing}"


def test_change_requests_exist():
    assert len(list((ROOT / "change_requests").glob("CR-*.md"))) >= 5


def test_env_is_gitignored():
    assert ".env" in (ROOT / ".gitignore").read_text(encoding="utf-8")
