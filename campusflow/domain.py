from dataclasses import dataclass
from enum import Enum, auto


class RegistrationStatus(Enum):
    ACTIVE = auto()
    WAITLISTED = auto()


@dataclass(frozen=True)
class Event:
    id: int
    title: str
    capacity: int
    owner_id: str


@dataclass(frozen=True)
class Registration:
    event_id: int
    user_id: str
    status: RegistrationStatus
    id: int | None = None
