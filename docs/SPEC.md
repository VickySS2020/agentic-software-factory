# CampusFlow Specification

References `REQUIREMENTS.md`; does not redefine it.

## Event creation
Valid input creates an Event; invalid capacity is rejected. Covers FR-01.

## List events
Returns current events in ID order. Covers FR-02.

## Register
- unknown event -> `EventNotFoundError`;
- space available -> registration stored;
- full -> `CapacityReachedError`.

Known starter gap: duplicate registration is not prevented. CR-003 addresses it.

## Cancel
Existing registration is removed; missing registration -> `RegistrationNotFoundError`.
