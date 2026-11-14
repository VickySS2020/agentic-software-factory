import pytest

from campusflow.repository import SQLiteCampusFlowRepository
from campusflow.service import CampusFlowService


@pytest.mark.xfail(reason="Known baseline defect; CR-003 must fix duplicates", strict=True)
def test_duplicate_registration_is_rejected():
    service = CampusFlowService(SQLiteCampusFlowRepository())
    event = service.create_event("Popular Event", 3, "owner-1")
    service.register(event.id, "student-1")
    service.register(event.id, "student-1")
    assert len(service.repository.list_registrations(event.id)) == 1
