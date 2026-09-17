import asyncio
import logging
import signal
import sys
from psycopg.rows import dict_row

from config import settings
from db.connection import init_pool, close_pool, get_db_connection
from rabbitmq.connection import rabbitmq_manager
from rabbitmq.consumer import JobConsumer
from workers.matching_worker import MatchingWorker
from workers.embedding_worker import EmbeddingWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("belong-workers")

matching_worker = MatchingWorker()
embedding_worker = EmbeddingWorker()

async def reconcile_pending_jobs():
    """Background loop to periodically claim and process pending jobs directly from PostgreSQL if RabbitMQ missed them."""
    logger.info("Pending DB job reconciler loop started.")
    while True:
        try:
            await asyncio.sleep(15)  # Reconcile check interval
            async with get_db_connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    # Claim pending jobs using atomic row locking
                    claim_sql = """
                        UPDATE jobs
                        SET status = 'running',
                            started_at = CURRENT_TIMESTAMP,
                            attempts = attempts + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = (
                            SELECT id FROM jobs
                            WHERE status = 'pending' AND available_at <= CURRENT_TIMESTAMP AND attempts < 3
                            ORDER BY created_at ASC
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        RETURNING id, user_id, type, payload;
                    """
                    await cur.execute(claim_sql)
                    job_row = await cur.fetchone()
                    await conn.commit()

            if job_row:
                job_id = str(job_row["id"])
                user_id = str(job_row["user_id"])
                job_type = job_row["type"]
                payload = job_row.get("payload") or {}
                payload["job_id"] = job_id
                payload["user_id"] = user_id

                logger.info(f"Reconciler claimed pending DB job {job_id} (type: {job_type})")

                try:
                    if job_type == "matching":
                        result = await matching_worker.execute(payload)
                    elif job_type == "embedding":
                        result = await embedding_worker.execute(payload)
                    else:
                        raise ValueError(f"Unknown job type: {job_type}")

                    async with get_db_connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE jobs SET status = 'completed', completed_at = CURRENT_TIMESTAMP, result = %s::jsonb WHERE id = %s;",
                                (json.dumps(result), job_id)
                            )
                            await conn.commit()

                    logger.info(f"Reconciler completed job {job_id}")

                except Exception as ex:
                    logger.error(f"Reconciler job execution error for {job_id}: {ex}", exc_info=True)
                    async with get_db_connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE jobs SET status = 'failed', completed_at = CURRENT_TIMESTAMP, error = %s WHERE id = %s;",
                                (str(ex), job_id)
                            )
                            await conn.commit()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in pending job reconciler loop: {e}")

import json

async def main():
    logger.info("Starting belong-workers engine...")
    await init_pool()

    # Try connecting to RabbitMQ
    consumer = JobConsumer()
    try:
        await rabbitmq_manager.connect()
        await consumer.start_listening()
        logger.info("RabbitMQ consumer listening for incoming job messages.")
    except Exception as e:
        logger.warning(f"Could not connect to RabbitMQ initially: {e}. Workers will rely on PostgreSQL pending job reconciler loop.")

    # Launch background DB reconciler loop
    reconciler_task = asyncio.create_task(reconcile_pending_jobs())

    # Keep worker running
    stop_event = asyncio.Event()

    def _shutdown():
        logger.info("Shutdown signal received.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass  # Windows signal handling fallback

    try:
        await stop_event.wait()
    finally:
        logger.info("Shutting down belong-workers...")
        reconciler_task.cancel()
        await rabbitmq_manager.close()
        await close_pool()
        logger.info("belong-workers cleanly terminated.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped manually.")
