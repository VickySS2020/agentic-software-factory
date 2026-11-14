from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .errors import CapacityReachedError, CampusFlowError, EventNotFoundError, RegistrationNotFoundError
from .repository import SQLiteCampusFlowRepository
from .service import CampusFlowService

app = FastAPI(title="CampusFlow", version="0.1.0")
repo = SQLiteCampusFlowRepository("campusflow.db")
service = CampusFlowService(repo)


class EventCreate(BaseModel):
    title: str
    capacity: int = Field(gt=0)
    owner_id: str


class RegistrationCreate(BaseModel):
    user_id: str


@app.get("/events")
def list_events():
    return service.list_events()


@app.post("/events", status_code=201)
def create_event(payload: EventCreate):
    return service.create_event(payload.title, payload.capacity, payload.owner_id)


@app.post("/events/{event_id}/registrations", status_code=201)
def register(event_id: int, payload: RegistrationCreate):
    try:
        return service.register(event_id, payload.user_id)
    except EventNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except CapacityReachedError as exc:
        raise HTTPException(409, str(exc)) from exc
    except CampusFlowError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/events/{event_id}/registrations/{user_id}", status_code=204)
def cancel(event_id: int, user_id: str):
    try:
        service.cancel(event_id, user_id)
    except (EventNotFoundError, RegistrationNotFoundError) as exc:
        raise HTTPException(404, str(exc)) from exc
