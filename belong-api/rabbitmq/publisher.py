import json
import logging
import os
from typing import Dict, Any, Optional
import aio_pika

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "belong.jobs")

class RabbitMQPublisher:
    """Async RabbitMQ message publisher for dispatching worker jobs."""

    def __init__(self):
        self.url = RABBITMQ_URL
        self.exchange_name = RABBITMQ_EXCHANGE

    async def publish_job(self, routing_key: str, payload: Dict[str, Any]) -> bool:
        """Publishes a job message to RabbitMQ exchange.

        Returns True if published successfully, False if RabbitMQ is unavailable.
        """
        try:
            connection = await aio_pika.connect_robust(self.url, timeout=3.0)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(
                    self.exchange_name,
                    aio_pika.ExchangeType.DIRECT,
                    durable=True
                )
                message_body = json.dumps(payload).encode("utf-8")
                message = aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json"
                )
                await exchange.publish(message, routing_key=routing_key)
                logger.info(f"Published job message to RabbitMQ (routing_key='{routing_key}', payload={payload})")
                return True
        except Exception as e:
            logger.warning(
                f"Failed to publish message to RabbitMQ ({e}). Job will remain 'pending' in PostgreSQL for worker reconciler."
            )
            return False

publisher = RabbitMQPublisher()
