from __future__ import annotations

import asyncio

from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from src.core.logger import get_module_logger
from src.events.connection import rabbitmq
from src.events.handler import handle_event
from src.events.queues import Queues
from src.events.schemas import incoming_event_adapter

logger = get_module_logger(__name__)


async def _process_message(message: AbstractIncomingMessage) -> None:
    try:
        event = incoming_event_adapter.validate_json(message.body)

        result = handle_event(event)
        if asyncio.iscoroutine(result):
            await result

        await message.ack()

    except ValidationError as e:
        logger.error("[receiver] invalid message schema: %s", e)
        await message.reject(requeue=False)

    except Exception as e:
        logger.exception("[receiver] failed to process message: %s", e)
        await message.reject(requeue=False)


async def receive_events() -> None:
    attempts = 5

    for attempt in range(attempts):
        try:
            await rabbitmq.connect()

            queue = await rabbitmq.declare_queue(
                Queues.MATCH_RESULTS,
                durable=True,
                for_consumer=True,
            )

            logger.info("[receiver] waiting for messages from %s", Queues.MATCH_RESULTS)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await _process_message(message)
        except Exception as e:
            logger.error(
                "[receiver] error while receiving messages, attempt %d: %s", attempt, e
            )
            await asyncio.sleep(5)
        finally:
            await rabbitmq.close()


async def main() -> None:
    await receive_events()


if __name__ == "__main__":
    asyncio.run(main())
