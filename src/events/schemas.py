from typing import Annotated, List, Literal

from pydantic import BaseModel, Field, TypeAdapter

from src.events.queues import Queues


class QueueEvent(BaseModel):
    queue: Queues


class _EventResult(BaseModel):
    event_id: int
    home_team_name: str
    away_team_name: str


class EventsResultRequest(QueueEvent):
    event_type: Literal["events_result"]
    events: List[_EventResult]
    date: str


class EventsResultResponse(QueueEvent):
    event_type: Literal["events_result"]
    events: list


IncomingEvent = Annotated[
    EventsResultRequest,
    Field(discriminator="event_type"),
]

incoming_event_adapter = TypeAdapter(IncomingEvent)
