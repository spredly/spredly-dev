from __future__ import annotations

import asyncio
from typing import Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message, connect_robust
from aio_pika.abc import (AbstractRobustChannel, AbstractRobustConnection,
                          AbstractRobustQueue)

from src.core.logger import get_module_logger
from src.settings import settings

logger = get_module_logger(__name__)


class RabbitMQ:
    def __init__(self) -> None:
        self._connection: Optional[AbstractRobustConnection] = None
        self._publish_channel: Optional[AbstractRobustChannel] = None
        self._consume_channel: Optional[AbstractRobustChannel] = None
        self._lock = asyncio.Lock()

    @property
    def amqp_url(self) -> str:
        return (
            f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASSWORD}"
            f"@{settings.RABBIT_HOST}:{settings.RABBIT_PORT}/"
        )

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        async with self._lock:
            if self._connection and not self._connection.is_closed:
                return

            logger.info(
                "[rabbitmq] connecting to %s:%s",
                settings.RABBIT_HOST,
                settings.RABBIT_PORT,
            )

            self._connection = await connect_robust(
                self.amqp_url,
                timeout=5,
                client_properties={"connection_name": "events-service"},
            )

            self._publish_channel = await self._connection.channel(
                publisher_confirms=True
            )

            self._consume_channel = await self._connection.channel()

            await self._consume_channel.set_qos(prefetch_count=1)

            logger.info("[rabbitmq] connected")

    async def close(self) -> None:
        if self._publish_channel and not self._publish_channel.is_closed:
            await self._publish_channel.close()

        if self._consume_channel and not self._consume_channel.is_closed:
            await self._consume_channel.close()

        if self._connection and not self._connection.is_closed:
            await self._connection.close()

        self._publish_channel = None
        self._consume_channel = None
        self._connection = None

    async def get_publish_channel(self) -> AbstractRobustChannel:
        await self.connect()
        assert self._publish_channel is not None
        return self._publish_channel

    async def get_consume_channel(self) -> AbstractRobustChannel:
        await self.connect()
        assert self._consume_channel is not None
        return self._consume_channel

    async def declare_queue(
        self,
        queue_name: str,
        *,
        durable: bool = True,
        for_consumer: bool = False,
    ) -> AbstractRobustQueue:
        channel = (
            await self.get_consume_channel()
            if for_consumer
            else await self.get_publish_channel()
        )
        return await channel.declare_queue(
            queue_name,
            durable=durable,
        )

    async def publish_json(self, queue_name: str, body: bytes) -> None:
        channel = await self.get_publish_channel()

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=queue_name,
        )


rabbitmq = RabbitMQ()
