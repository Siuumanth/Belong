import json
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, status
from psycopg.rows import dict_row

from db.connection import get_db_connection
from jobs.repository import job_repository
from matching.schemas import (
    JobCreateResponse,
    JobStatusResponse,
    MatchCandidateResponse,
    MatchesListResponse,
)
from profile.repository import ProfileRepository
from rabbitmq.publisher import publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matching"])

@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_matching_job(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id_override: Optional[UUID] = None
):
    """Enqueues an asynchronous compatibility matching job for the authenticated user.

    The user ID is derived strictly from the X-User-ID header injected by the Auth Gateway.
    """
    effective_user_id_str = x_user_id
    if not effective_user_id_str and user_id_override:
        effective_user_id_str = str(user_id_override)

    if not effective_user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context. X-User-ID header required."
        )

    try:
        user_id = UUID(effective_user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format."
        )

    # 1. Verify user profile exists
    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found."
        )

    # 2. Create job in PostgreSQL
    payload = {"user_id": str(user_id)}
    job_data = await job_repository.create_job(
        user_id=user_id,
        job_type="matching",
        payload=payload
    )

    job_id = UUID(str(job_data["id"]))
    mq_payload = {
        "job_id": str(job_id),
        "user_id": str(user_id),
        "type": "matching"
    }

    # 3. Publish to RabbitMQ (non-blocking fallback if RabbitMQ is offline)
    await publisher.publish_job(routing_key="matching", payload=mq_payload)

    return JobCreateResponse(
        job_id=job_id,
        user_id=user_id,
        type="matching",
        status=job_data["status"],
        created_at=job_data["created_at"]
    )

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_matching_job_status(job_id: UUID):
    """Poll status and progress details of a matching job."""
    job_data = await job_repository.get_job_by_id(job_id)
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found."
        )

    return JobStatusResponse(
        job_id=UUID(str(job_data["id"])),
        user_id=UUID(str(job_data["user_id"])),
        type=job_data["type"],
        status=job_data["status"],
        attempts=job_data.get("attempts", 0),
        error=job_data.get("error"),
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
        result=job_data.get("result")
    )

@router.get("/{user_id}", response_model=MatchesListResponse)
async def get_user_matches(user_id: UUID):
    """Retrieves qualitative compatibility match breakdowns for a user."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT user_b_id, dimension_results, strong_alignments,
                       complementary_alignments, shared_alignments,
                       potential_conflicts, dealbreaker_violations, uncertainties,
                       created_at, updated_at
                FROM compatibility_results
                WHERE user_a_id = %s
                ORDER BY updated_at DESC;
            """
            await cur.execute(query, (str(user_id),))
            rows = await cur.fetchall()

    matches: List[MatchCandidateResponse] = []
    for r in rows:
        matches.append(MatchCandidateResponse(
            user_b_id=UUID(str(r["user_b_id"])),
            overall_verdict=r.get("dimension_results", {}).get("overall_verdict", "unclear")
            if isinstance(r.get("dimension_results"), dict) and "overall_verdict" in r.get("dimension_results", {})
            else "unclear",
            dimension_results=r.get("dimension_results") or {},
            strong_alignments=r.get("strong_alignments") or [],
            complementary_alignments=r.get("complementary_alignments") or [],
            shared_alignments=r.get("shared_alignments") or [],
            potential_conflicts=r.get("potential_conflicts") or [],
            dealbreaker_violations=r.get("dealbreaker_violations") or [],
            uncertainties=r.get("uncertainties") or []
        ))

    return MatchesListResponse(
        user_id=user_id,
        total_matches=len(matches),
        matches=matches
    )
