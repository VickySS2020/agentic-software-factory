# AGENTS.md — Repository Operating Contract

## Read first

1. `docs/REQUIREMENTS.md`
2. `docs/SPEC.md`
3. `docs/ARCHITECTURE.md`
4. active `change_requests/CR-*.md`
5. `docs/REPO_MAP.md`

## Source of truth

- Requirements / AC: `docs/REQUIREMENTS.md`.
- `SPEC.md` defines verifiable behavior without redefining requirements.
- Architecture constraints: `ARCHITECTURE.md`.
- Change Requests scope a specific run.

## Standard validation

```bash
python scripts/verify_repo.py
```

## Rules

- Do not invent requirements.
- Do not edit requirements/spec just to make code pass.
- Do not weaken tests.
- Keep changes scoped.
- Never expose secrets.
- Never merge automatically.
- Reviewer and Security are read-only on first review.

## Stop conditions

Stop for human input when requirements conflict/are ambiguous, permissions are insufficient, an irreversible action is proposed, evidence is insufficient, or a dependency/API appears invented.
