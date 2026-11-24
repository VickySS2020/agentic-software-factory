# Architecture

## Product

```text
FastAPI adapter
      |
      v
CampusFlowService        <- business rules
      |
      v
SQLiteCampusFlowRepository
      |
      v
SQLite
```

Rules: API does not implement business policy; Repository does not decide business policy; Service coordinates behavior.

## Factory

```text
Change Request -> Intake -> Planner -> HUMAN GATE -> Coder -> Verification
                                                   -> Reviewer + Security
                                                   -> HUMAN REVIEW
                                                   -> Fix / Re-review
                                                   -> HUMAN RELEASE
                                                   -> PR Evidence
```

The Reviewer must inspect requirements, architecture, changed code, tests, verification evidence and actual APIs/dependencies. It must not treat the Coder's own claims as proof.

## Workflow

1. Human creates or selects CHANGE_REQUEST
2. INTAKE Agent reconstructs context, affected requirements/ACs and detects ambiguity.
      - 2.1 If there is ambiguity, STOP and Human Gate. The factory does not invent policy nor continue until it receives a human decision.
3. PLANNER Agent creates implementation-plan.md without modifying code
4. HUMAN GATE #1: Tech Lead approves (APPROVED), modifies (APPROVED), or rejects the plan (REJECTED). The coder remains locked until APPROVED.
5. The CODER Agent implements only the approved plan on its own branch and produces coder-report.md. The coder agent only works in code located in src/ and tests/ directories.
6. TEST ANALYST Agent inspects test gaps, negative/boundary/regression cases and proposes or adds only authorized tests.
7. VERIFICATION GATE runs deterministic pytest, ruff, and repository checks.
      - 7.1. If Verification fails, it returns to Coder/Fix and repeats Verification. A change with failing checks does NOT reach Reviewer or Security.
8. If Verification passes, Reviewer and Security run independently and read-only on requirements, architecture, diff, real APIs/dependencies, tests, and evidence.
9. HUMAN GATE #2: Human Reviewer decides each finding: ACCEPTED / REJECTED / MODIFIED / DEFERRED.
10. If there are ACCEPTED/MODIFIED blocking findings, Coder only corrects those authorized findings.
11. Re-verification and relevant security scans are performed; any failures return to the correction cycle.
12. Reviewers and Security teams perform re-reviews/re-checks of their respective findings and verify that the fixes do not introduce new regressions or risks. New blocking findings are returned to Human Review/Fix.
13. Evidence Agent/logic consolidates evidence-summary.md, traceability.md, and factory-run.json using only
actual evidence produced by the run.
14. The Release Manager reviews the consolidated evidence and decides READY FOR HUMAN MERGE or NOT READY. The final merge is performed exclusively by a human.

Maximum automated state: READY FOR HUMAN MERGE. The merge remains human-only.