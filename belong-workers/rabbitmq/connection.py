import logging
import asyncio
from typing import Optional
import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel

from config import settings

logger = logging.getLogger(__name__)

class RabbitMQManager:
    """Manages persistent aio-pika robust connection and channels."""

    def __init__(self):
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractRobustChannel] = None

    async def connect(self) -> AbstractRobustConnection:
        if self._connection is None or self._connection.is_closed:
            logger.info(f"Connecting to RabbitMQ at {settings.RABBITMQ_URL}...")
            self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            logger.info("RabbitMQ connection established.")
        return self._connection

    async def get_channel(self) -> AbstractRobustChannel:
        connection = await self.connect()
        if self._channel is None or self._channel.is_closed:
            self._channel = await connection.channel()
            # Declare exchange and queues
            exchange = await self._channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            queue_matching = await self._channel.declare_queue(
                settings.RABBITMQ_QUEUE_MATCHING,
                durable=True
            )
            await queue_matching.bind(exchange, routing_key="matching")

            queue_embedding = await self._channel.declare_queue(
                settings.RABBITMQ_QUEUE_EMBEDDING,
                durable=True
            )
            await queue_embedding.bind(exchange, routing_key="embedding")

            logger.info("RabbitMQ exchange and queues declared successfully.")
        return self._channel

    async def close(self):
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("RabbitMQ connection closed.")

rabbitmq_manager = RabbitMQManager()
