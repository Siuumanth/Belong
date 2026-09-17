import json
import logging
import os
import sys
from typing import Dict, Any, List
from uuid import UUID

from psycopg.rows import dict_row

from db.connection import get_db_connection
from matching.compatibility import PairwiseCompatibilityAgent
from matching.ranking import rank_candidates
from matching.retrieval import CandidateRetriever

logger = logging.getLogger(__name__)

class MatchingWorker:
    """Worker task that executes Stage 1 pgvector candidate retrieval and Stage 2 LangGraph pairwise reasoning."""

    def __init__(self):
        self.retriever = CandidateRetriever()
        self.compatibility_agent = PairwiseCompatibilityAgent()

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        job_id = payload.get("job_id")
        user_id_str = payload.get("user_id")

        if not user_id_str:
            raise ValueError("Payload missing required field 'user_id'")

        user_id = UUID(user_id_str)
        logger.info(f"MatchingWorker starting matching execution for user {user_id} (job_id: {job_id})")

        # 1. Fetch User A profile
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT user_id, age, gender, orientation, relationship_goal, profile FROM profiles WHERE user_id = %s;",
                    (str(user_id),)
                )
                user_a_row = await cur.fetchone()

        if not user_a_row:
            raise ValueError(f"User profile for user {user_id} not found in database.")

        user_a_profile = user_a_row.get("profile") or {}
        user_a_profile["age"] = user_a_row.get("age")
        user_a_profile["gender"] = user_a_row.get("gender")
        user_a_profile["relationship_goal"] = user_a_row.get("relationship_goal")

        # 2. Stage 1: Hard filters + pgvector candidate retrieval
        candidate_matches = await self.retriever.retrieve_candidates(user_id)
        logger.info(f"Stage 1 retrieved {len(candidate_matches)} candidates for user {user_id}")

        if not candidate_matches:
            logger.info(f"No eligible candidate matches found for user {user_id}.")
            return {"user_id": str(user_id), "total_matches": 0, "matches_persisted": 0}

        # 3. Stage 2: Pairwise LLM Compatibility Reasoning for each candidate
        evaluated_candidates = []
        for candidate in candidate_matches:
            user_b_profile = candidate.profile or {}
            user_b_profile["age"] = candidate.age
            user_b_profile["gender"] = candidate.gender
            user_b_profile["relationship_goal"] = candidate.relationship_goal

            try:
                output = await self.compatibility_agent.evaluate_pair(
                    user_a_profile=user_a_profile,
                    user_b_profile=user_b_profile
                )

                evaluated_candidates.append({
                    "candidate_user_id": candidate.user_id,
                    "stage1_combined_score": candidate.combined_score,
                    "compatibility_output": output
                })
            except Exception as e:
                logger.error(f"Failed pairwise evaluation between {user_id} and {candidate.user_id}: {e}")

        # 4. Rank candidates deterministically
        ranked_candidates = rank_candidates(evaluated_candidates)
        logger.info(f"Ranked {len(ranked_candidates)} candidates for user {user_id}")

        # 5. Persist results into compatibility_results table in Postgres
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                for rank_idx, item in enumerate(ranked_candidates):
                    user_b_id = item["candidate_user_id"]
                    output = item["compatibility_output"]

                    # Convert dimension_results to jsonable dict
                    dimension_json = json.dumps(output.dimension_results.model_dump())
                    strong_alignments_json = json.dumps(output.strong_alignments)
                    potential_conflicts_json = json.dumps(output.potential_conflicts)
                    dealbreaker_violations_json = json.dumps(output.dealbreaker_violations)
                    uncertainties_json = json.dumps(output.uncertainties)

                    upsert_sql = """
                        INSERT INTO compatibility_results (
                            user_a_id, user_b_id, dimension_results,
                            strong_alignments, potential_conflicts,
                            dealbreaker_violations, uncertainties,
                            reasoning_version, updated_at
                        )
                        VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, 'v1', CURRENT_TIMESTAMP)
                        ON CONFLICT (user_a_id, user_b_id, reasoning_version)
                        DO UPDATE SET
                            dimension_results = EXCLUDED.dimension_results,
                            strong_alignments = EXCLUDED.strong_alignments,
                            potential_conflicts = EXCLUDED.potential_conflicts,
                            dealbreaker_violations = EXCLUDED.dealbreaker_violations,
                            uncertainties = EXCLUDED.uncertainties,
                            updated_at = CURRENT_TIMESTAMP;
                    """
                    await cur.execute(
                        upsert_sql,
                        (
                            str(user_id),
                            str(user_b_id),
                            dimension_json,
                            strong_alignments_json,
                            potential_conflicts_json,
                            dealbreaker_violations_json,
                            uncertainties_json
                        )
                    )
                await conn.commit()

        logger.info(f"Persisted {len(ranked_candidates)} compatibility results for user {user_id}")
        return {
            "user_id": str(user_id),
            "total_matches": len(ranked_candidates),
            "matches_persisted": len(ranked_candidates)
        }
