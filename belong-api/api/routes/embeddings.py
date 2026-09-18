from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional

from jobs.repository import job_repository
from matching.schemas import JobCreateResponse
from profile.repository import ProfileRepository
from rabbitmq.publisher import publisher

router = APIRouter(tags=["embeddings"])

@router.post(
    "/profiles/{user_id}/embeddings",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous canonical semantic embedding generation for a profile",
)
async def generate_profile_embeddings(user_id: UUID):
    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found."
        )

    payload = {"user_id": str(user_id)}
    job_data = await job_repository.create_job(
        user_id=user_id,
        job_type="embedding",
        payload=payload
    )

    job_id = UUID(str(job_data["id"]))
    mq_payload = {
        "job_id": str(job_id),
        "user_id": str(user_id),
        "type": "embedding"
    }

    await publisher.publish_job(routing_key="embedding", payload=mq_payload)

    return JobCreateResponse(
        job_id=job_id,
        user_id=user_id,
        type="embedding",
        status=job_data["status"],
        created_at=job_data["created_at"]
    )

@router.get(
    "/profiles/{user_id}/embeddings",
    summary="Fetch embedding status and canonical source text for a profile",
)
async def get_profile_embedding_status(user_id: UUID):
    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    from db.connection import get_db_connection
    from psycopg.rows import dict_row

    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT embedding_source_text,
                       (self_embedding IS NOT NULL) AS has_self_embedding,
                       (wants_embedding IS NOT NULL) AS has_wants_embedding,
                       updated_at
                FROM profiles
                WHERE user_id = %s;
            """
            await cur.execute(query, (str(user_id),))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

            return {
                "user_id": str(user_id),
                "has_self_embedding": row["has_self_embedding"],
                "has_wants_embedding": row["has_wants_embedding"],
                "embedding_source_text": row["embedding_source_text"],
                "updated_at": row["updated_at"],
            }
