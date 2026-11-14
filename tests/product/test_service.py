import pytest

from campusflow.errors import CapacityReachedError, EventNotFoundError, InvalidEventError, RegistrationNotFoundError
from campusflow.repository import SQLiteCampusFlowRepository
from campusflow.service import CampusFlowService


@pytest.fixture
def service():
    return CampusFlowService(SQLiteCampusFlowRepository())


def test_create_and_list_event(service):
    event = service.create_event("AI Meetup", 2, "prof-1")
    assert event.id == 1
    assert service.list_events() == [event]


def test_event_capacity_must_be_positive(service):
    with pytest.raises(InvalidEventError):
        service.create_event("Invalid", 0, "prof-1")


def test_register_when_space_is_available(service):
    event = service.create_event("Bachata Tech", 2, "owner-1")
    registration = service.register(event.id, "student-1")
    assert registration.user_id == "student-1"


def test_registration_rejects_unknown_event(service):
    with pytest.raises(EventNotFoundError):
        service.register(999, "student-1")


def test_registration_rejects_when_event_is_full(service):
    event = service.create_event("Small Event", 1, "owner-1")
    service.register(event.id, "student-1")
    with pytest.raises(CapacityReachedError):
        service.register(event.id, "student-2")


def test_cancel_existing_registration(service):
    event = service.create_event("Workshop", 2, "owner-1")
    service.register(event.id, "student-1")
    service.cancel(event.id, "student-1")
    assert not service.repository.has_registration(event.id, "student-1")


def test_cancel_missing_registration_is_clear(service):
    event = service.create_event("Workshop", 2, "owner-1")
    with pytest.raises(RegistrationNotFoundError):
        service.cancel(event.id, "student-1")
