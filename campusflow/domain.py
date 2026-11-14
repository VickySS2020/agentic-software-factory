from dataclasses import dataclass


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
