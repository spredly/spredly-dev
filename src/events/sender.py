from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from src.events.connection import rabbitmq

T = TypeVar("T", bound=BaseModel)


async def send_event(message: T) -> None:
    try:
        await rabbitmq.connect()

        await rabbitmq.declare_queue(
            message.queue,
            durable=True,
            for_consumer=False,
        )

        body = message.model_dump_json().encode("utf-8")
        await rabbitmq.publish_json(message.queue, body)
    finally:
        await rabbitmq.close()
