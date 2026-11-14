# CR-001 — Event Waitlist

## Goal
When an event reaches capacity, a new registration must enter a waitlist instead of being rejected. When an active participant cancels, the first waiting user is promoted.

## Acceptance Criteria
- AC-CR001.1: below capacity remains active.
- AC-CR001.2: full event -> WAITLISTED.
- AC-CR001.3: waitlist is FIFO.
- AC-CR001.4: cancellation promotes first waiting user.
- AC-CR001.5: baseline event/list behavior does not regress.

## Constraints
Business rules remain in Service. Add deterministic tests. No external infrastructure.
