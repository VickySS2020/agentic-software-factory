# CampusFlow Requirements

## FR-01 — Events
Organizers can create events with title, capacity (>0) and owner identifier.

- AC-01.1: created event receives a unique integer ID.
- AC-01.2: capacity <= 0 is rejected.

## FR-02 — Event discovery
Users can list existing events.

- AC-02.1: list exposes ID, title, capacity and owner.

## FR-03 — Registration
A user can register while capacity is available.

- AC-03.1: unknown event is rejected.
- AC-03.2: available capacity -> registration accepted.
- AC-03.3: full capacity -> baseline rejects registration.

CR-001 intentionally changes AC-03.3 by introducing a waitlist.

## FR-04 — Cancellation
A registered user can cancel an existing registration.

- AC-04.1: existing registration is removed.
- AC-04.2: missing registration is reported clearly.

## NFR-01 — Architecture
Business rules live in Service. Dependency direction: `API -> Service -> Repository`.

## NFR-02 — Verification
Business-rule changes require automated tests.

## NFR-03 — Security
Secrets stay out of source control. Agent roles follow least privilege.

## NFR-04 — Evidence
Each factory run is auditable under `runs/<CR-ID>/`.
