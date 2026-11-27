import pytest
from campusflow.domain import RegistrationStatus
from campusflow.errors import RegistrationNotFoundError
from campusflow.repository import SQLiteCampusFlowRepository
from campusflow.service import CampusFlowService

@pytest.fixture
def service():
    return CampusFlowService(SQLiteCampusFlowRepository())

# Regression: test that cancellation of a non-existent registration fails
def test_cancel_non_existent_registration_fails(service):
    event = service.create_event("Test Event", 5, "owner-1")
    with pytest.raises(RegistrationNotFoundError):
        service.cancel(event.id, "ghost-user")

# Boundary: test waitlist promotion for multiple users
def test_waitlist_multiple_promotions(service):
    event = service.create_event("Test Event", 1, "owner-1")
    service.register(event.id, "user-1") # ACTIVE
    service.register(event.id, "user-2") # WAITLISTED
    service.register(event.id, "user-3") # WAITLISTED
    
    # Cancel user-1: user-2 promoted
    service.cancel(event.id, "user-1")
    regs = {r.user_id: r for r in service.repository.list_registrations(event.id)}
    assert regs["user-2"].status == RegistrationStatus.ACTIVE
    assert regs["user-3"].status == RegistrationStatus.WAITLISTED
    
    # Cancel user-2: user-3 promoted
    service.cancel(event.id, "user-2")
    regs = {r.user_id: r for r in service.repository.list_registrations(event.id)}
    assert regs["user-3"].status == RegistrationStatus.ACTIVE
