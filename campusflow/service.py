from .errors import CapacityReachedError, EventNotFoundError, InvalidEventError, RegistrationNotFoundError
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
        if self.repository.count_registrations(event_id) >= event.capacity:
            raise CapacityReachedError(f"event {event_id} is full")
        # Deliberate gap for CR-003: no duplicate check yet.
        return self.repository.add_registration(event_id, user_id)

    def cancel(self, event_id: int, user_id: str) -> None:
        if self.repository.get_event(event_id) is None:
            raise EventNotFoundError(f"event {event_id} not found")
        if not self.repository.remove_registration(event_id, user_id):
            raise RegistrationNotFoundError(
                f"user {user_id!r} is not registered for event {event_id}"
            )
