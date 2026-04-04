from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar, cast

from pydantic import BaseModel

from src.core.logger import get_module_logger
from src.events.schemas import EventsResultResponse
from src.services.results_service import ResultsService

logger = get_module_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_HANDLERS: dict[type[BaseModel], Callable[[BaseModel], Awaitable[None]]] = {}


def register_handler(
    model: type[T],
) -> Callable[[Callable[[T], Awaitable[None]]], Callable[[T], Awaitable[None]]]:
    def decorator(
        func: Callable[[T], Awaitable[None]],
    ) -> Callable[[T], Awaitable[None]]:
        _HANDLERS[model] = cast(Callable[[BaseModel], Awaitable[None]], func)
        return func

    return decorator


@register_handler(EventsResultResponse)
async def handle_match_results(response: EventsResultResponse) -> None:
    await ResultsService.save_results(response.events)


async def handle_event(event: BaseModel) -> None:
    handler = _HANDLERS.get(type(event))
    if handler is not None:
        await handler(event)
        return

    for model, fallback_handler in _HANDLERS.items():
        if isinstance(event, model):
            await fallback_handler(event)
            return

    raise ValueError(f"No handler registered for event type: {type(event).__name__}")
