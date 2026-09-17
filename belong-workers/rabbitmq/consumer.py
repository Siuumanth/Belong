import json
import logging
import asyncio
from typing import Dict, Any
import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from config import settings
from db.connection import get_db_connection
from rabbitmq.connection import rabbitmq_manager
from workers.matching_worker import MatchingWorker
from workers.embedding_worker import EmbeddingWorker

logger = logging.getLogger(__name__)

class JobConsumer:
    """RabbitMQ consumer that dispatches tasks to worker classes and manages DB job lifecycle."""

    def __init__(self):
        self.matching_worker = MatchingWorker()
        self.embedding_worker = EmbeddingWorker()

    async def _update_job_db(
        self, 
        job_id: str, 
        status: str, 
        result: Any = None, 
        error: str = None, 
        increment_attempts: bool = False
    ):
        """Helper function to atomically update status in PostgreSQL jobs table."""
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                fields = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
                params = [status]

                if increment_attempts:
                    fields.append("attempts = attempts + 1")
                if status == "running":
                    fields.append("started_at = CURRENT_TIMESTAMP")
                elif status in ("completed", "failed"):
                    fields.append("completed_at = CURRENT_TIMESTAMP")
                if result is not None:
                    fields.append("result = %s::jsonb")
                    params.append(json.dumps(result))
                if error is not None:
                    fields.append("error = %s")
                    params.append(error)

                params.append(job_id)
                query = f"UPDATE jobs SET {', '.join(fields)} WHERE id = %s;"
                await cur.execute(query, params)
                await conn.commit()

    async def process_message(self, message: AbstractIncomingMessage):
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body.decode("utf-8"))
                job_id = body.get("job_id")
                job_type = body.get("type")

                if not job_id:
                    logger.error("Received RabbitMQ message missing 'job_id'")
                    return

                logger.info(f"Received RabbitMQ job {job_id} of type '{job_type}'")

                # Mark job running in Postgres
                await self._update_job_db(job_id=job_id, status="running", increment_attempts=True)

                if job_type == "matching":
                    result = await self.matching_worker.execute(body)
                elif job_type == "embedding":
                    result = await self.embedding_worker.execute(body)
                else:
                    raise ValueError(f"Unknown job type: {job_type}")

                # Mark job completed
                await self._update_job_db(job_id=job_id, status="completed", result=result)
                logger.info(f"Successfully processed job {job_id}")

            except Exception as e:
                logger.error(f"Error processing RabbitMQ job {job_id if 'job_id' in locals() else 'unknown'}: {e}", exc_info=True)
                if 'job_id' in locals() and job_id:
                    await self._update_job_db(job_id=job_id, status="failed", error=str(e))

    async def start_listening(self):
        """Starts listening on RabbitMQ queues."""
        channel = await rabbitmq_manager.get_channel()
        await channel.set_qos(prefetch_count=5)

        queue_matching = await channel.get_queue(settings.RABBITMQ_QUEUE_MATCHING)
        queue_embedding = await channel.get_queue(settings.RABBITMQ_QUEUE_EMBEDDING)

        logger.info(f"Starting consumer loop on queues '{settings.RABBITMQ_QUEUE_MATCHING}' and '{settings.RABBITMQ_QUEUE_EMBEDDING}'...")
        await queue_matching.consume(self.process_message)
        await queue_embedding.consume(self.process_message)
