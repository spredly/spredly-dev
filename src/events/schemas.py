from typing import Annotated, List, Literal

from pydantic import BaseModel, Field, TypeAdapter

from src.events.queues import Queues


class QueueEvent(BaseModel):
    queue: Queues


class _EventResultRequest(BaseModel):
    event_id: int
    home_team_name: str
    away_team_name: str

class _EventResultResponse(BaseModel):
    event_id: int
    score1: int
    score2: int

class EventsResultRequest(QueueEvent):
    event_type: Literal["events_result_request"]
    events: List[_EventResultRequest]
    date: str


class EventsResultResponse(QueueEvent):
    event_type: Literal["events_result_response"]
    events: List[_EventResultResponse]


IncomingEvent = Annotated[
    EventsResultRequest | EventsResultResponse,
    Field(discriminator="event_type"),
]

incoming_event_adapter = TypeAdapter(IncomingEvent)
