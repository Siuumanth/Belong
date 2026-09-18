import json
import logging
import os
import sys
from typing import Dict, Any
from uuid import UUID

from psycopg.rows import dict_row

from db.connection import get_db_connection
from embeddings.serializer import CanonicalSerializer
from embeddings.client import EmbeddingClient

logger = logging.getLogger(__name__)

class EmbeddingWorker:
    """Worker task that handles asynchronous deterministic semantic serialization and embedding generation."""

    def __init__(self):
        self.serializer = CanonicalSerializer()
        self.embedding_client = EmbeddingClient()

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        job_id = payload.get("job_id")
        user_id_str = payload.get("user_id")

        if not user_id_str:
            raise ValueError("Payload missing required field 'user_id'")

        user_id = UUID(user_id_str)
        logger.info(f"EmbeddingWorker processing user {user_id} (job_id: {job_id})")

        # 1. Fetch profile JSON from Postgres
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT user_id, profile FROM profiles WHERE user_id = %s;",
                    (str(user_id),)
                )
                row = await cur.fetchone()

        if not row:
            raise ValueError(f"Profile for user {user_id} not found.")

        profile_data = row.get("profile") or {}

        # 2. Run canonical semantic serializer
        self_text, wants_text = self.serializer.serialize(profile_data)

        # 3. Generate vectors
        self_vec = await self.embedding_client.embed_text(self_text) if self_text else None
        wants_vec = await self.embedding_client.embed_text(wants_text) if wants_text else None

        source_text_dict = {
            "self_text": self_text,
            "wants_text": wants_text
        }

        # 4. Update profiles table in Postgres
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                update_sql = """
                    UPDATE profiles
                    SET self_embedding = %s::vector,
                        wants_embedding = %s::vector,
                        embedding_source_text = %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s;
                """
                await cur.execute(
                    update_sql,
                    (
                        str(self_vec) if self_vec else None,
                        str(wants_vec) if wants_vec else None,
                        json.dumps(source_text_dict),
                        str(user_id)
                    )
                )
                await conn.commit()

        logger.info(f"EmbeddingWorker completed vector updates for user {user_id}")
        return {
            "user_id": str(user_id),
            "self_embedding_generated": self_vec is not None,
            "wants_embedding_generated": wants_vec is not None
        }

if __name__ == "__main__":
    import asyncio
    from db.connection import init_pool, close_pool
    from rabbitmq.connection import rabbitmq_manager
    from rabbitmq.consumer import JobConsumer

    async def run_standalone():
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting standalone Embedding Worker process...")
        await init_pool()
        consumer = JobConsumer()
        try:
            await rabbitmq_manager.connect()
            await consumer.start_listening_embedding()
            stop = asyncio.Event()
            await stop.wait()
        finally:
            await rabbitmq_manager.close()
            await close_pool()

    try:
        asyncio.run(run_standalone())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Embedding Worker stopped.")

