class CampusFlowError(Exception):
    """Base product error."""


class InvalidEventError(CampusFlowError):
    pass


class EventNotFoundError(CampusFlowError):
    pass


class CapacityReachedError(CampusFlowError):
    pass


class RegistrationNotFoundError(CampusFlowError):
    pass
