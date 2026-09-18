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
    """RabbitMQ consumer that dispatches tasks to dedicated worker classes and manages DB job lifecycle."""

    def __init__(self):
        self.matching_worker = MatchingWorker()
        self.embedding_worker = EmbeddingWorker()

    async def _update_job_db(
        self, 
        job_id: str, 
        status: str, 
        result: Any = None, 
        error: str | None = None, 
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

    async def process_embedding_message(self, message: AbstractIncomingMessage):
        """Dedicated consumer callback for the belong.embedding queue."""
        async with message.process(requeue=False):
            job_id: str | None = None
            try:
                body = json.loads(message.body.decode("utf-8"))
                job_id = body.get("job_id")

                if not job_id:
                    logger.error("Received RabbitMQ embedding message missing 'job_id'")
                    return

                logger.info(f"Received RabbitMQ embedding job {job_id}")

                await self._update_job_db(job_id=job_id, status="running", increment_attempts=True)
                result = await self.embedding_worker.execute(body)
                await self._update_job_db(job_id=job_id, status="completed", result=result)
                logger.info(f"Successfully processed embedding job {job_id}")

            except Exception as e:
                logger.error(f"Error processing embedding job {job_id or 'unknown'}: {e}", exc_info=True)
                if job_id:
                    await self._update_job_db(job_id=job_id, status="failed", error=str(e))

    async def process_matching_message(self, message: AbstractIncomingMessage):
        """Dedicated consumer callback for the belong.matching queue."""
        async with message.process(requeue=False):
            job_id: str | None = None
            try:
                body = json.loads(message.body.decode("utf-8"))
                job_id = body.get("job_id")

                if not job_id:
                    logger.error("Received RabbitMQ matching message missing 'job_id'")
                    return

                logger.info(f"Received RabbitMQ matching job {job_id}")

                await self._update_job_db(job_id=job_id, status="running", increment_attempts=True)
                result = await self.matching_worker.execute(body)
                await self._update_job_db(job_id=job_id, status="completed", result=result)
                logger.info(f"Successfully processed matching job {job_id}")

            except Exception as e:
                logger.error(f"Error processing matching job {job_id or 'unknown'}: {e}", exc_info=True)
                if job_id:
                    await self._update_job_db(job_id=job_id, status="failed", error=str(e))

    async def start_listening_embedding(self):
        """Starts listening exclusively on the belong.embedding queue."""
        channel = await rabbitmq_manager.get_channel()
        await channel.set_qos(prefetch_count=5)
        queue_embedding = await channel.get_queue(settings.RABBITMQ_QUEUE_EMBEDDING)
        logger.info(f"Starting dedicated Embedding consumer loop on queue '{settings.RABBITMQ_QUEUE_EMBEDDING}'...")
        await queue_embedding.consume(self.process_embedding_message)

    async def start_listening_matching(self):
        """Starts listening exclusively on the belong.matching queue."""
        channel = await rabbitmq_manager.get_channel()
        await channel.set_qos(prefetch_count=5)
        queue_matching = await channel.get_queue(settings.RABBITMQ_QUEUE_MATCHING)
        logger.info(f"Starting dedicated Matching consumer loop on queue '{settings.RABBITMQ_QUEUE_MATCHING}'...")
        await queue_matching.consume(self.process_matching_message)

    async def start_listening(self):
        """Starts listening on both embedding and matching queues for V1 combined worker process."""
        await self.start_listening_embedding()
        await self.start_listening_matching()
