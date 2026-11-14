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
