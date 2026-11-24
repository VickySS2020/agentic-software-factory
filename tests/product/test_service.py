import pytest

from campusflow.domain import RegistrationStatus
from campusflow.errors import EventNotFoundError, InvalidEventError, RegistrationNotFoundError
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
    assert registration.status == RegistrationStatus.ACTIVE


def test_registration_rejects_unknown_event(service):
    with pytest.raises(EventNotFoundError):
        service.register(999, "student-1")


# AC-CR001.1 & AC-CR001.2: register into full event -> WAITLISTED
def test_registration_into_full_event_is_waitlisted(service):
    event = service.create_event("Small Event", 1, "owner-1")
    service.register(event.id, "student-1")
    reg2 = service.register(event.id, "student-2")
    assert reg2.status == RegistrationStatus.WAITLISTED
    assert service.repository.count_registrations(event.id, status=RegistrationStatus.ACTIVE) == 1
    assert (
        service.repository.count_registrations(event.id, status=RegistrationStatus.WAITLISTED)
        == 1
    )


# AC-CR001.3 & AC-CR001.4: FIFO and promotion
def test_waitlist_fifo_and_promotion(service):
    event = service.create_event("Small Event", 1, "owner-1")
    service.register(event.id, "student-1")  # ACTIVE
    service.register(event.id, "student-2")  # WAITLISTED
    service.register(event.id, "student-3")  # WAITLISTED

    # Cancel student-1, student-2 should be promoted
    service.cancel(event.id, "student-1")

    registrations = {
        r.user_id: r for r in service.repository.list_registrations(event.id)
    }
    assert registrations["student-2"].status == RegistrationStatus.ACTIVE
    assert registrations["student-3"].status == RegistrationStatus.WAITLISTED


def test_cancel_existing_registration(service):
    event = service.create_event("Workshop", 2, "owner-1")
    service.register(event.id, "student-1")
    service.cancel(event.id, "student-1")
    assert not service.repository.has_registration(event.id, "student-1")


def test_cancel_missing_registration_is_clear(service):
    event = service.create_event("Workshop", 2, "owner-1")
    with pytest.raises(RegistrationNotFoundError):
        service.cancel(event.id, "student-1")
