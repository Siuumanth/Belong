import json
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Header, status
from psycopg.rows import dict_row

from db.connection import get_db_connection
from jobs.repository import job_repository
from matching.schemas import (
    AnalyzeMatchRequest,
    JobCreateResponse,
    JobStatusResponse,
    MatchCandidateResponse,
    MatchesListResponse,
    RetrievalListResponse,
    RetrievalOptions,
)
from matching.retrieval import default_retriever
from matching.compatibility import PairwiseCompatibilityAgent
from profile.repository import ProfileRepository
from rabbitmq.publisher import publisher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matching"])

@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_matching_job(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id_override: Optional[UUID] = None
):
    """Enqueues an asynchronous full compatibility matching batch job for the authenticated user."""
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

    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for user {user_id} not found."
        )

    payload = {"user_id": str(user_id)}
    job_data = await job_repository.create_job(
        user_id=user_id,
        job_type="matching",
        payload=payload
    )

    job_id = UUID(str(job_data["id"]))

    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO match_runs (id, user_id, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT (id) DO NOTHING;
                """,
                (str(job_id), str(user_id))
            )
            await conn.commit()

    mq_payload = {
        "job_id": str(job_id),
        "user_id": str(user_id),
        "type": "matching"
    }

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

# ---------------------------------------------------------------------------
# FIND MATCHES: Stage 1 Candidate Match Retrieval (No LLM reasoning)
# ---------------------------------------------------------------------------

@router.get("/candidates/{user_id}", response_model=RetrievalListResponse)
async def get_candidate_matches(
    user_id: UUID,
    candidate_pool_limit: Optional[int] = None,
    pre_rank_limit: Optional[int] = None,
    max_distance_km: Optional[int] = None,
):
    """Find Matches (Stage 1 Candidate Retrieval): Fetches top-K candidate matches from DB using hard filters + pgvector similarity without running LLM compatibility analysis."""
    options = RetrievalOptions(
        candidate_pool_limit=candidate_pool_limit,
        pre_rank_limit=pre_rank_limit,
        max_distance_km=max_distance_km,
    )
    try:
        candidates = await default_retriever.retrieve_candidates(user_id=user_id, options=options)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Candidate match retrieval failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate retrieval error: {e}"
        )

    return RetrievalListResponse(
        user_id=user_id,
        total_candidates=len(candidates),
        candidates=candidates
    )

@router.post("/candidates", response_model=RetrievalListResponse)
async def post_candidate_matches(
    options: Optional[RetrievalOptions] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id_override: Optional[UUID] = None,
):
    """Find Matches (Stage 1 Candidate Retrieval): POST variant accepting options in request body or X-User-ID header."""
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

    try:
        candidates = await default_retriever.retrieve_candidates(user_id=user_id, options=options)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Candidate match retrieval failed for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate retrieval error: {e}"
        )

    return RetrievalListResponse(
        user_id=user_id,
        total_candidates=len(candidates),
        candidates=candidates
    )

@router.get("/retrieval/{user_id}", response_model=RetrievalListResponse)
async def get_candidate_retrieval(
    user_id: UUID,
    candidate_pool_limit: Optional[int] = None,
    pre_rank_limit: Optional[int] = None,
    max_distance_km: Optional[int] = None,
):
    """Alias for candidate retrieval (hard constraint SQL filters + vector similarity recall)."""
    return await get_candidate_matches(
        user_id=user_id,
        candidate_pool_limit=candidate_pool_limit,
        pre_rank_limit=pre_rank_limit,
        max_distance_km=max_distance_km,
    )

# ---------------------------------------------------------------------------
# ANALYZE DEEPER: Stage 2 On-Demand LLM Matchmaking
# ---------------------------------------------------------------------------

async def _perform_pairwise_llm_analysis(user_a_id: UUID, candidate_b_id: UUID) -> MatchCandidateResponse:
    """Helper function to execute Stage 2 Pairwise LLM reasoning and store output in compatibility_results."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT user_id, name, age, gender, orientation, relationship_goal, profile FROM profiles WHERE user_id = %s;",
                (str(user_a_id),)
            )
            user_a_row = await cur.fetchone()

            await cur.execute(
                "SELECT user_id, name, age, gender, orientation, relationship_goal, profile FROM profiles WHERE user_id = %s;",
                (str(candidate_b_id),)
            )
            user_b_row = await cur.fetchone()

    if not user_a_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User profile for user {user_a_id} not found."
        )
    if not user_b_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile for user {candidate_b_id} not found."
        )

    user_a_profile = user_a_row.get("profile") or {}
    user_a_profile["age"] = user_a_row.get("age")
    user_a_profile["gender"] = user_a_row.get("gender")
    user_a_profile["relationship_goal"] = user_a_row.get("relationship_goal")

    user_b_profile = user_b_row.get("profile") or {}
    user_b_profile["age"] = user_b_row.get("age")
    user_b_profile["gender"] = user_b_row.get("gender")
    user_b_profile["relationship_goal"] = user_b_row.get("relationship_goal")

    agent = PairwiseCompatibilityAgent()
    try:
        output = await agent.evaluate_pair(
            user_a_profile=user_a_profile,
            user_b_profile=user_b_profile
        )
    except Exception as e:
        logger.error(f"Failed pairwise LLM reasoning between {user_a_id} and {candidate_b_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM compatibility reasoning failed: {e}"
        )

    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "UPDATE compatibility_results SET is_latest = false WHERE user_a_id = %s AND user_b_id = %s AND is_latest = true;",
                (str(user_a_id), str(candidate_b_id))
            )

            dimension_json = json.dumps(output.dimension_results.model_dump())
            complementary_json = json.dumps(output.complementary_alignments)
            shared_json = json.dumps(output.shared_alignments)
            strong_json = json.dumps(output.strong_alignments or (output.complementary_alignments + output.shared_alignments))
            conflicts_json = json.dumps(output.potential_conflicts)
            dealbreakers_json = json.dumps(output.dealbreaker_violations)
            uncertainties_json = json.dumps(output.uncertainties)
            reasoning_text = getattr(output, "overall_reasoning", "") or ""

            insert_sql = """
                INSERT INTO compatibility_results (
                    match_id, user_a_id, user_b_id, overall_verdict, overall_reasoning, dimension_results,
                    strong_alignments, complementary_alignments, shared_alignments,
                    potential_conflicts, dealbreaker_violations, uncertainties,
                    reasoning_version, is_latest, updated_at
                )
                VALUES (gen_random_uuid(), %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, 'v1', true, CURRENT_TIMESTAMP)
                RETURNING id, match_id, created_at, updated_at;
            """
            await cur.execute(
                insert_sql,
                (
                    str(user_a_id),
                    str(candidate_b_id),
                    getattr(output, "overall_verdict", "unclear") or "unclear",
                    reasoning_text,
                    dimension_json,
                    strong_json,
                    complementary_json,
                    shared_json,
                    conflicts_json,
                    dealbreakers_json,
                    uncertainties_json
                )
            )
            result_row = await cur.fetchone()
            await conn.commit()

    return MatchCandidateResponse(
        id=UUID(str(result_row["id"])),
        match_id=UUID(str(result_row["match_id"])) if result_row.get("match_id") else None,
        user_a_id=user_a_id,
        user_b_id=candidate_b_id,
        user_b_name=user_b_row.get("name"),
        overall_verdict=output.overall_verdict,
        overall_reasoning=output.overall_reasoning or "",
        dimension_results=output.dimension_results.model_dump(),
        strong_alignments=output.strong_alignments,
        complementary_alignments=output.complementary_alignments,
        shared_alignments=output.shared_alignments,
        potential_conflicts=output.potential_conflicts,
        dealbreaker_violations=output.dealbreaker_violations,
        uncertainties=output.uncertainties,
        created_at=result_row.get("created_at"),
        updated_at=result_row.get("updated_at")
    )

@router.post("/analyze", response_model=MatchCandidateResponse)
async def analyze_candidate_deeper(
    req: AnalyzeMatchRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Analyze Deeper: Runs LLM pairwise compatibility reasoning on-demand for a single candidate match."""
    user_id_str = str(req.user_id) if req.user_id else x_user_id
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context. X-User-ID header or user_id in payload required."
        )
    try:
        user_a_id = UUID(user_id_str)
        candidate_b_id = req.candidate_user_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid UUID format for user_id or candidate_user_id."
        )

    return await _perform_pairwise_llm_analysis(user_a_id, candidate_b_id)

@router.post("/analyze/{candidate_user_id}", response_model=MatchCandidateResponse)
async def analyze_candidate_by_path(
    candidate_user_id: UUID,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id_override: Optional[UUID] = None,
):
    """Analyze Deeper: Runs LLM pairwise compatibility reasoning on-demand for candidate_user_id path parameter."""
    effective_user_id_str = x_user_id
    if not effective_user_id_str and user_id_override:
        effective_user_id_str = str(user_id_override)

    if not effective_user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context. X-User-ID header required."
        )

    try:
        user_a_id = UUID(effective_user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_id format."
        )

    return await _perform_pairwise_llm_analysis(user_a_id, candidate_user_id)

# ---------------------------------------------------------------------------
# MATCH RESULTS RETRIEVAL
# ---------------------------------------------------------------------------

@router.get("/details/pair/{candidate_user_id}", response_model=MatchCandidateResponse)
async def get_match_detail_by_pair(
    candidate_user_id: UUID,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    user_id_override: Optional[UUID] = None
):
    """Retrieves existing full detailed qualitative compatibility analysis for a specific candidate user pair."""
    effective_user_id_str = x_user_id
    if not effective_user_id_str and user_id_override:
        effective_user_id_str = str(user_id_override)

    if not effective_user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context. X-User-ID header required."
        )

    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.id, c.match_id, c.user_a_id, c.user_b_id, p.name AS user_b_name,
                       c.overall_verdict, c.overall_reasoning, c.dimension_results,
                       c.strong_alignments, c.complementary_alignments, c.shared_alignments,
                       c.potential_conflicts, c.dealbreaker_violations, c.uncertainties,
                       c.created_at, c.updated_at
                FROM compatibility_results c
                LEFT JOIN profiles p ON c.user_b_id = p.user_id
                WHERE c.user_a_id = %s AND c.user_b_id = %s AND c.is_latest = true
                ORDER BY c.updated_at DESC
                LIMIT 1;
            """
            await cur.execute(query, (effective_user_id_str, str(candidate_user_id)))
            r = await cur.fetchone()

    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compatibility match result between user {effective_user_id_str} and candidate {candidate_user_id} not found."
        )

    return MatchCandidateResponse(
        id=UUID(str(r["id"])),
        match_id=UUID(str(r["match_id"])) if r.get("match_id") else None,
        user_a_id=UUID(str(r["user_a_id"])) if r.get("user_a_id") else None,
        user_b_id=UUID(str(r["user_b_id"])),
        user_b_name=r.get("user_b_name"),
        overall_verdict=r.get("overall_verdict") or "unclear",
        overall_reasoning=r.get("overall_reasoning") or "",
        dimension_results=r.get("dimension_results") or {},
        strong_alignments=r.get("strong_alignments") or [],
        complementary_alignments=r.get("complementary_alignments") or [],
        shared_alignments=r.get("shared_alignments") or [],
        potential_conflicts=r.get("potential_conflicts") or [],
        dealbreaker_violations=r.get("dealbreaker_violations") or [],
        uncertainties=r.get("uncertainties") or [],
        created_at=r.get("created_at"),
        updated_at=r.get("updated_at")
    )

@router.get("/{user_id}", response_model=MatchesListResponse)
async def get_user_matches(user_id: UUID):
    """Retrieves all latest qualitative compatibility match breakdowns for a user."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.id, c.match_id, c.user_a_id, c.user_b_id, p.name AS user_b_name,
                       c.overall_verdict, c.overall_reasoning, c.dimension_results,
                       c.strong_alignments, c.complementary_alignments, c.shared_alignments,
                       c.potential_conflicts, c.dealbreaker_violations, c.uncertainties,
                       c.created_at, c.updated_at
                FROM compatibility_results c
                LEFT JOIN profiles p ON c.user_b_id = p.user_id
                WHERE c.user_a_id = %s AND c.is_latest = true
                ORDER BY c.updated_at DESC;
            """
            await cur.execute(query, (str(user_id),))
            rows = await cur.fetchall()

    matches: List[MatchCandidateResponse] = []
    for r in rows:
        matches.append(MatchCandidateResponse(
            id=UUID(str(r["id"])) if r.get("id") else None,
            match_id=UUID(str(r["match_id"])) if r.get("match_id") else None,
            user_a_id=UUID(str(r["user_a_id"])) if r.get("user_a_id") else None,
            user_b_id=UUID(str(r["user_b_id"])),
            user_b_name=r.get("user_b_name"),
            overall_verdict=r.get("overall_verdict") or "unclear",
            overall_reasoning=r.get("overall_reasoning") or "",
            dimension_results=r.get("dimension_results") or {},
            strong_alignments=r.get("strong_alignments") or [],
            complementary_alignments=r.get("complementary_alignments") or [],
            shared_alignments=r.get("shared_alignments") or [],
            potential_conflicts=r.get("potential_conflicts") or [],
            dealbreaker_violations=r.get("dealbreaker_violations") or [],
            uncertainties=r.get("uncertainties") or [],
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at")
        ))

    return MatchesListResponse(
        user_id=user_id,
        total_matches=len(matches),
        matches=matches
    )

@router.get("/jobs/{job_id}/results", response_model=MatchesListResponse)
async def get_matching_job_results(job_id: UUID):
    """Retrieves all qualitative compatibility match candidate breakdowns generated by a specific matching job run."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.id, c.match_id, c.user_a_id, c.user_b_id, p.name AS user_b_name,
                       c.overall_verdict, c.overall_reasoning, c.dimension_results,
                       c.strong_alignments, c.complementary_alignments, c.shared_alignments,
                       c.potential_conflicts, c.dealbreaker_violations, c.uncertainties,
                       c.created_at, c.updated_at
                FROM compatibility_results c
                LEFT JOIN profiles p ON c.user_b_id = p.user_id
                WHERE c.match_id = %s
                ORDER BY c.updated_at DESC;
            """
            await cur.execute(query, (str(job_id),))
            rows = await cur.fetchall()

    if not rows:
        job = await job_repository.get_job_by_id(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Matching job {job_id} not found."
            )
        user_id = UUID(str(job["user_id"]))
        return MatchesListResponse(user_id=user_id, total_matches=0, matches=[])

    user_a_id = UUID(str(rows[0]["user_a_id"]))
    matches: List[MatchCandidateResponse] = []
    for r in rows:
        matches.append(MatchCandidateResponse(
            id=UUID(str(r["id"])) if r.get("id") else None,
            match_id=UUID(str(r["match_id"])) if r.get("match_id") else None,
            user_a_id=UUID(str(r["user_a_id"])) if r.get("user_a_id") else None,
            user_b_id=UUID(str(r["user_b_id"])),
            user_b_name=r.get("user_b_name"),
            overall_verdict=r.get("overall_verdict") or "unclear",
            overall_reasoning=r.get("overall_reasoning") or "",
            dimension_results=r.get("dimension_results") or {},
            strong_alignments=r.get("strong_alignments") or [],
            complementary_alignments=r.get("complementary_alignments") or [],
            shared_alignments=r.get("shared_alignments") or [],
            potential_conflicts=r.get("potential_conflicts") or [],
            dealbreaker_violations=r.get("dealbreaker_violations") or [],
            uncertainties=r.get("uncertainties") or [],
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at")
        ))

    return MatchesListResponse(
        user_id=user_a_id,
        total_matches=len(matches),
        matches=matches
    )

@router.get("/details/{result_id}", response_model=MatchCandidateResponse)
async def get_match_detail(result_id: UUID):
    """Retrieves full detailed qualitative compatibility analysis for a specific match record ID."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            query = """
                SELECT c.id, c.match_id, c.user_a_id, c.user_b_id, p.name AS user_b_name,
                       c.overall_verdict, c.overall_reasoning, c.dimension_results,
                       c.strong_alignments, c.complementary_alignments, c.shared_alignments,
                       c.potential_conflicts, c.dealbreaker_violations, c.uncertainties,
                       c.created_at, c.updated_at
                FROM compatibility_results c
                LEFT JOIN profiles p ON c.user_b_id = p.user_id
                WHERE c.id = %s;
            """
            await cur.execute(query, (str(result_id),))
            r = await cur.fetchone()

    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compatibility match result {result_id} not found."
        )

    return MatchCandidateResponse(
        id=UUID(str(r["id"])),
        match_id=UUID(str(r["match_id"])) if r.get("match_id") else None,
        user_a_id=UUID(str(r["user_a_id"])) if r.get("user_a_id") else None,
        user_b_id=UUID(str(r["user_b_id"])),
        user_b_name=r.get("user_b_name"),
        overall_verdict=r.get("overall_verdict") or "unclear",
        overall_reasoning=r.get("overall_reasoning") or "",
        dimension_results=r.get("dimension_results") or {},
        strong_alignments=r.get("strong_alignments") or [],
        complementary_alignments=r.get("complementary_alignments") or [],
        shared_alignments=r.get("shared_alignments") or [],
        potential_conflicts=r.get("potential_conflicts") or [],
        dealbreaker_violations=r.get("dealbreaker_violations") or [],
        uncertainties=r.get("uncertainties") or [],
        created_at=r.get("created_at"),
        updated_at=r.get("updated_at")
    )
