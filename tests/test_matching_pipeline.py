"""
Matching Pipeline Integration Test
===================================
Exercises the full Stage 1 → Stage 2 → DB persist path by calling
MatchingWorker.execute() directly — no HTTP, no RabbitMQ needed.

What this proves:
  1. CandidateRetriever.retrieve_candidates() returns >= 1 result for Bob
     (verifies the @> jsonb_build_array fix for preferred_genders).
  2. PairwiseCompatibilityAgent produces a valid output for each candidate.
  3. At least one row is inserted into compatibility_results with
     user_a_id = Bob's UUID.

Pre-conditions (already satisfied by tests/results.md data):
  - Bob  (198001d8-a5e2-4112-af89-3f398cd1e4dd) has both embeddings,
    gender='male', preferred_genders=['female'], relationship_goal='long-term'
  - Alice (53ee7eb9-17c9-4d54-b058-3bf0294157a2) has both embeddings,
    gender='female', preferred_genders=['male'], relationship_goal='long-term'

Markers:
  - e2e   : requires running Postgres
  - live  : makes real Groq LLM calls

Run:
    pytest tests/test_matching_pipeline.py -m "e2e and live" -v -s
"""

# ---------------------------------------------------------------------------
# Windows: psycopg async requires SelectorEventLoop, not ProactorEventLoop.
# MUST be set before any asyncio import is used for loop creation.
# ---------------------------------------------------------------------------
import sys
import selectors
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from psycopg.rows import dict_row

# ---------------------------------------------------------------------------
# Path setup — belong-workers must be first so its modules shadow belong-api
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "belong-workers"))
sys.path.insert(1, str(ROOT / "belong-api"))

# ---------------------------------------------------------------------------
# Load env vars — try belong-workers/.env first, then root .env.
# Ensures GROQ_API_KEY etc. are available when running tests directly.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    # Root .env has the real keys — load it first with override=True so it wins
    # over any placeholder values in belong-workers/.env
    _root_env   = ROOT / ".env"
    _worker_env = ROOT / "belong-workers" / ".env"
    if _root_env.exists():
        load_dotenv(_root_env, override=True)
    if _worker_env.exists():
        load_dotenv(_worker_env, override=False)  # fills in any worker-only vars
except ImportError:
    pass  # dotenv not available; rely on env vars already being set

from db.connection import get_db_connection, init_pool, close_pool
from workers.matching_worker import MatchingWorker

logger = logging.getLogger(__name__)

# Known UUIDs from tests/results.md
BOB_USER_ID   = UUID("198001d8-a5e2-4112-af89-3f398cd1e4dd")
ALICE_USER_ID = UUID("53ee7eb9-17c9-4d54-b058-3bf0294157a2")


# ---------------------------------------------------------------------------
# Per-test DB pool fixture (function scope keeps each test independent)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def db_pool():
    """Open and close the worker DB pool around each test."""
    await init_pool()
    yield
    await close_pool()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _count_compatibility_results(user_a_id: UUID) -> int:
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM compatibility_results WHERE user_a_id = %s;",
                (str(user_a_id),)
            )
            row = await cur.fetchone()
            return row[0] if row else 0


async def _get_latest_compatibility_rows(user_a_id: UUID):
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT cr.user_b_id, cr.overall_reasoning, cr.dimension_results,
                       cr.strong_alignments, cr.complementary_alignments,
                       cr.shared_alignments, cr.potential_conflicts,
                       cr.dealbreaker_violations, cr.uncertainties,
                       cr.is_latest, cr.match_id, cr.updated_at,
                       mr.status AS match_run_status
                FROM compatibility_results cr
                LEFT JOIN match_runs mr ON mr.id = cr.match_id
                WHERE cr.user_a_id = %s AND cr.is_latest = true
                ORDER BY cr.updated_at DESC;
                """,
                (str(user_a_id),)
            )
            return await cur.fetchall()


async def _verify_profiles_have_embeddings() -> bool:
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT user_id, name, gender, preferred_genders,
                       self_embedding IS NOT NULL  AS has_self,
                       wants_embedding IS NOT NULL AS has_wants
                FROM profiles
                WHERE user_id = ANY(%s::uuid[]);
                """,
                ([str(BOB_USER_ID), str(ALICE_USER_ID)],)
            )
            rows = await cur.fetchall()

    found = {UUID(str(r["user_id"])): r for r in rows}
    ok = True
    for uid, label in [(BOB_USER_ID, "Bob"), (ALICE_USER_ID, "Alice")]:
        if uid not in found:
            logger.error(f"Pre-condition FAILED: {label} ({uid}) not in profiles table")
            ok = False
            continue
        r = found[uid]
        if not r["has_self"] or not r["has_wants"]:
            logger.error(
                f"Pre-condition FAILED: {label} missing embeddings "
                f"(has_self={r['has_self']}, has_wants={r['has_wants']})"
            )
            ok = False
        else:
            logger.info(
                f"Pre-condition OK: {label} ({uid}) "
                f"gender={r['gender']} preferred_genders={r['preferred_genders']}"
            )
    return ok


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.e2e
@pytest.mark.live
async def test_stage1_retrieval_finds_alice_for_bob():
    """
    Stage 1 only: Bob's retriever must return Alice as a candidate.

    This is the direct regression test for the preferred_genders JSONB bug.
    The @> fix means Alice (preferred_genders=['male']) is NOT filtered out
    when Bob (gender='male') runs retrieval.
    """
    from matching.retrieval import CandidateRetriever
    from matching.schemas import RetrievalOptions

    retriever = CandidateRetriever(
        options=RetrievalOptions(
            require_mutual_gender=True,
            require_mutual_age=True,
            require_mutual_relationship_goal=True,
        )
    )

    candidates = await retriever.retrieve_candidates(BOB_USER_ID)

    assert len(candidates) >= 1, (
        f"Stage 1 returned 0 candidates for Bob. "
        f"The @> jsonb_build_array fix may not be active or Alice's profile is missing embeddings."
    )

    candidate_ids = [c.user_id for c in candidates]
    assert ALICE_USER_ID in candidate_ids, (
        f"Alice ({ALICE_USER_ID}) not in Bob's candidates. "
        f"Found: {candidate_ids}"
    )

    alice = next(c for c in candidates if c.user_id == ALICE_USER_ID)
    logger.info(
        f"✓ Stage 1 found Alice: cosine_similarity={alice.cosine_similarity}, "
        f"combined_score={alice.combined_score}"
    )
    assert alice.combined_score > 0.0


@pytest.mark.e2e
@pytest.mark.live
async def test_matching_worker_inserts_compatibility_results():
    """
    Full pipeline: MatchingWorker.execute() for Bob must insert at least one
    row into compatibility_results with user_a_id = Bob's UUID and is_latest = true.

    This is the end-to-end regression for 'compatibility_results has 0 rows'.
    """
    # Count rows before
    before = await _count_compatibility_results(BOB_USER_ID)
    logger.info(f"compatibility_results rows for Bob before run: {before}")

    # Pre-condition check
    embeddings_ok = await _verify_profiles_have_embeddings()
    assert embeddings_ok, "Pre-conditions not met — Bob or Alice missing embeddings."

    # Run the worker directly (no RabbitMQ needed)
    job_id = str(uuid4())
    worker = MatchingWorker()
    result = await worker.execute({
        "job_id": job_id,
        "user_id": str(BOB_USER_ID),
        "type": "matching",
    })

    logger.info(f"MatchingWorker result: {result}")

    # --- Core assertion: at least 1 match ---
    assert result["total_matches"] >= 1, (
        f"MatchingWorker reported 0 total_matches. "
        f"Stage 1 returned no candidates — check the retrieval fix."
    )
    assert result["matches_persisted"] >= 1, (
        f"MatchingWorker reported 0 matches_persisted even though candidates were found."
    )

    after = await _count_compatibility_results(BOB_USER_ID)
    logger.info(f"compatibility_results rows for Bob after run: {after}")
    assert after > before, (
        f"No new rows in compatibility_results after worker run "
        f"(before={before}, after={after})."
    )

    # --- Structural assertions on the persisted rows ---
    rows = await _get_latest_compatibility_rows(BOB_USER_ID)
    assert len(rows) >= 1

    for row in rows:
        user_b = UUID(str(row["user_b_id"]))
        logger.info(
            f"  Match: user_b={user_b}, "
            f"match_run_status={row['match_run_status']}, "
            f"updated_at={row['updated_at']}"
        )

        # match_run must be completed
        assert row["match_run_status"] == "completed", (
            f"match_run for job {job_id} is '{row['match_run_status']}', expected 'completed'."
        )

        # dimension_results must be a non-empty dict
        dim = row["dimension_results"]
        assert isinstance(dim, dict) and len(dim) > 0, (
            f"dimension_results is empty or wrong type for user_b={user_b}"
        )
        for expected_dim in ("emotional_needs", "core_values", "lifestyle", "conflict_style"):
            assert expected_dim in dim, (
                f"dimension_results missing '{expected_dim}' for user_b={user_b}"
            )

        # overall_reasoning must be a non-empty string
        assert isinstance(row["overall_reasoning"], str) and len(row["overall_reasoning"]) > 10, (
            f"overall_reasoning is missing or too short for user_b={user_b}: "
            f"'{row['overall_reasoning']}'"
        )

        # alignment lists must exist
        for field in ("strong_alignments", "complementary_alignments", "shared_alignments",
                      "potential_conflicts", "dealbreaker_violations", "uncertainties"):
            assert isinstance(row[field], list), (
                f"Field '{field}' should be a list, got {type(row[field])} for user_b={user_b}"
            )

    # --- Alice specifically should appear ---
    result_user_b_ids = [UUID(str(r["user_b_id"])) for r in rows]
    assert ALICE_USER_ID in result_user_b_ids, (
        f"Alice ({ALICE_USER_ID}) not in Bob's compatibility_results. "
        f"Found user_b_ids: {result_user_b_ids}"
    )
    logger.info("✓ Alice found in Bob's compatibility_results.")
