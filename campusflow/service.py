from .domain import RegistrationStatus
from .errors import EventNotFoundError, InvalidEventError, RegistrationNotFoundError
from .repository import SQLiteCampusFlowRepository


class CampusFlowService:
    def __init__(self, repository: SQLiteCampusFlowRepository) -> None:
        self.repository = repository

    def create_event(self, title: str, capacity: int, owner_id: str):
        if not title.strip():
            raise InvalidEventError("title is required")
        if capacity <= 0:
            raise InvalidEventError("capacity must be greater than zero")
        if not owner_id.strip():
            raise InvalidEventError("owner_id is required")
        return self.repository.create_event(title.strip(), capacity, owner_id.strip())

    def list_events(self):
        return self.repository.list_events()

    def register(self, event_id: int, user_id: str):
        event = self.repository.get_event(event_id)
        if event is None:
            raise EventNotFoundError(f"event {event_id} not found")

        active_count = self.repository.count_registrations(
            event_id, status=RegistrationStatus.ACTIVE
        )

        if active_count < event.capacity:
            status = RegistrationStatus.ACTIVE
        else:
            status = RegistrationStatus.WAITLISTED

        return self.repository.add_registration(event_id, user_id, status)

    def cancel(self, event_id: int, user_id: str) -> None:
        if self.repository.get_event(event_id) is None:
            raise EventNotFoundError(f"event {event_id} not found")

        # Need to determine if the one being cancelled was ACTIVE
        registrations = self.repository.list_registrations(event_id)
        reg_to_cancel = next((r for r in registrations if r.user_id == user_id), None)

        if reg_to_cancel is None:
            raise RegistrationNotFoundError(
                f"user {user_id!r} is not registered for event {event_id}"
            )

        was_active = reg_to_cancel.status == RegistrationStatus.ACTIVE

        self.repository.remove_registration(event_id, user_id)

        if was_active:
            next_waitlisted = self.repository.get_next_waitlisted(event_id)
            if next_waitlisted:
                self.repository.update_registration_status(
                    next_waitlisted.id, RegistrationStatus.ACTIVE
                )
