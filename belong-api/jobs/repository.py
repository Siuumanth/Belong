import json
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from psycopg.rows import dict_row

from db.connection import get_db_connection

logger = logging.getLogger(__name__)

class JobRepository:
    """Repository for managing async jobs in PostgreSQL."""

    async def create_job(self, user_id: UUID, job_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new job record with 'pending' status."""
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                job_id = uuid4()
                insert_sql = """
                    INSERT INTO jobs (id, user_id, type, status, payload, created_at, updated_at)
                    VALUES (%s, %s, %s, 'pending', %s::jsonb, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, user_id, type, status, payload, attempts, error, available_at, started_at, completed_at, created_at;
                """
                await cur.execute(insert_sql, (str(job_id), str(user_id), job_type, json.dumps(payload)))
                row = await cur.fetchone()
                await conn.commit()
                return dict(row) if row else {}

    async def get_job_by_id(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetches job status and details by job_id."""
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, user_id, type, status, payload, result, attempts, error,
                           available_at, started_at, completed_at, created_at, updated_at
                    FROM jobs
                    WHERE id = %s;
                """
                await cur.execute(query, (str(job_id),))
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_jobs_by_user(self, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches recent jobs for a specific user."""
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, user_id, type, status, result, attempts, error, created_at, completed_at
                    FROM jobs
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """
                await cur.execute(query, (str(user_id), limit))
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

job_repository = JobRepository()
