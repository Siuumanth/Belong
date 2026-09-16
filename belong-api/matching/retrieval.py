import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

try:
    from psycopg.rows import dict_row
except (ImportError, ModuleNotFoundError):
    dict_row = None

from config import settings
from db.connection import get_db_connection
from matching.models import CandidateMatch, RetrievalOptions

logger = logging.getLogger(__name__)

class CandidateRetriever:
    """Handles Stage 1 Matching: Hard constraint SQL filters + pgvector candidate retrieval."""

    def __init__(self, options: Optional[RetrievalOptions] = None):
        self.options = options or RetrievalOptions()

    def _get_effective_options(self, custom_options: Optional[RetrievalOptions] = None) -> Dict[str, Any]:
        """Merges instance options, call-specific options, and default config settings."""
        opts = custom_options or self.options
        return {
            "candidate_pool_limit": opts.candidate_pool_limit or settings.MATCHING_CANDIDATE_POOL_LIMIT,
            "pre_rank_limit": opts.pre_rank_limit or settings.MATCHING_PRE_RANK_LIMIT,
            "max_distance_km": opts.max_distance_km or settings.MATCHING_MAX_DISTANCE_KM_DEFAULT,
            "min_similarity_threshold": (
                opts.min_similarity_threshold 
                if opts.min_similarity_threshold is not None 
                else settings.MATCHING_MIN_SIMILARITY_THRESHOLD
            ),
            "bidirectional_weight": (
                opts.bidirectional_weight 
                if opts.bidirectional_weight is not None 
                else settings.MATCHING_BIDIRECTIONAL_WEIGHT
            ),
            "require_mutual_age": opts.require_mutual_age,
            "require_mutual_gender": opts.require_mutual_gender,
            "require_mutual_relationship_goal": opts.require_mutual_relationship_goal,
        }

    async def retrieve_candidates(
        self, 
        user_id: UUID, 
        options: Optional[RetrievalOptions] = None
    ) -> List[CandidateMatch]:
        """Retrieves and pre-ranks candidate profiles for user_id based on hard filters & vector similarity."""
        config = self._get_effective_options(options)

        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                # 1. Fetch user's profile and vectors
                user_query = """
                    SELECT user_id, age, gender, orientation, latitude, longitude,
                           relationship_goal, preferred_age_min, preferred_age_max,
                           max_distance_km, preferred_genders, required_relationship_goal,
                           self_embedding, wants_embedding
                    FROM profiles
                    WHERE user_id = %s;
                """
                await cur.execute(user_query, (str(user_id),))
                user_row = await cur.fetchone()

                if not user_row:
                    raise ValueError(f"User profile with id {user_id} not found.")

                if user_row.get("wants_embedding") is None:
                    logger.warning(f"User {user_id} does not have wants_embedding. Cannot perform vector matching.")
                    return []

                # Parse User A fields
                user_lat = user_row.get("latitude")
                user_lon = user_row.get("longitude")
                user_age = user_row.get("age")
                user_gender = user_row.get("gender")
                user_pref_genders = user_row.get("preferred_genders") or []
                user_pref_age_min = user_row.get("preferred_age_min")
                user_pref_age_max = user_row.get("preferred_age_max")
                user_max_distance = user_row.get("max_distance_km") or config["max_distance_km"]
                user_req_goal = user_row.get("required_relationship_goal")
                user_goal = user_row.get("relationship_goal")
                wants_vec_str = str(user_row["wants_embedding"])
                self_vec_str = str(user_row["self_embedding"]) if user_row.get("self_embedding") is not None else None

                # 2. Build dynamic SQL query for Candidate Recall
                conditions = [
                    "p.user_id != %(user_id)s",
                    "p.self_embedding IS NOT NULL"
                ]
                params: Dict[str, Any] = {
                    "user_id": str(user_id),
                    "wants_vec": wants_vec_str,
                    "pool_limit": config["candidate_pool_limit"]
                }

                # Hard Filter: Gender & Preferred Genders
                if config["require_mutual_gender"]:
                    # User A prefers specific genders
                    if user_pref_genders and len(user_pref_genders) > 0:
                        conditions.append("p.gender = ANY(%(user_pref_genders)s)")
                        params["user_pref_genders"] = user_pref_genders

                    # Candidate B prefers User A's gender (if Candidate specifies preferences)
                    if user_gender:
                        conditions.append(
                            "(p.preferred_genders = '[]'::jsonb OR p.preferred_genders ? %(user_gender)s)"
                        )
                        params["user_gender"] = user_gender

                # Hard Filter: Mutual Age Constraints
                if config["require_mutual_age"]:
                    if user_pref_age_min is not None:
                        conditions.append("(p.age IS NULL OR p.age >= %(user_pref_age_min)s)")
                        params["user_pref_age_min"] = user_pref_age_min
                    if user_pref_age_max is not None:
                        conditions.append("(p.age IS NULL OR p.age <= %(user_pref_age_max)s)")
                        params["user_pref_age_max"] = user_pref_age_max
                    
                    if user_age is not None:
                        conditions.append("(p.preferred_age_min IS NULL OR p.preferred_age_min <= %(user_age)s)")
                        conditions.append("(p.preferred_age_max IS NULL OR p.preferred_age_max >= %(user_age)s)")
                        params["user_age"] = user_age

                # Hard Filter: Relationship Goals
                if config["require_mutual_relationship_goal"]:
                    if user_req_goal:
                        conditions.append("(p.relationship_goal IS NULL OR p.relationship_goal = %(user_req_goal)s)")
                        params["user_req_goal"] = user_req_goal
                    if user_goal:
                        conditions.append(
                            "(p.required_relationship_goal IS NULL OR p.required_relationship_goal = %(user_goal)s)"
                        )
                        params["user_goal"] = user_goal

                # Hard Filter: Geographic Distance (Haversine)
                haversine_sql = "NULL::float"
                if user_lat is not None and user_lon is not None:
                    params["user_lat"] = user_lat
                    params["user_lon"] = user_lon
                    params["user_max_dist"] = user_max_distance
                    
                    # Haversine distance in km
                    haversine_sql = """
                        (6371 * acos(
                            LEAST(1.0, GREATEST(-1.0, 
                                cos(radians(%(user_lat)s)) * cos(radians(p.latitude)) * 
                                cos(radians(p.longitude) - radians(%(user_lon)s)) + 
                                sin(radians(%(user_lat)s)) * sin(radians(p.latitude))
                            ))
                        ))
                    """
                    # Distance filter applies if candidate has lat/lon
                    conditions.append(f"""
                        (p.latitude IS NULL OR p.longitude IS NULL OR (
                            {haversine_sql} <= LEAST(%(user_max_dist)s, COALESCE(p.max_distance_km, %(user_max_dist)s))
                        ))
                    """)

                # Reverse vector distance selection
                if self_vec_str:
                    params["self_vec"] = self_vec_str
                    reverse_dist_sql = "CASE WHEN p.wants_embedding IS NOT NULL THEN (p.wants_embedding <=> %(self_vec)s::vector) ELSE NULL END"
                else:
                    reverse_dist_sql = "NULL::float"

                where_clause = " AND ".join(conditions)

                retrieval_query = f"""
                    SELECT p.user_id, p.age, p.gender, p.orientation, p.relationship_goal,
                           p.latitude, p.longitude, p.profile,
                           {haversine_sql} AS distance_km,
                           (p.self_embedding <=> %(wants_vec)s::vector) AS cosine_distance,
                           {reverse_dist_sql} AS reverse_cosine_distance
                    FROM profiles p
                    WHERE {where_clause}
                    ORDER BY (p.self_embedding <=> %(wants_vec)s::vector) ASC
                    LIMIT %(pool_limit)s;
                """

                await cur.execute(retrieval_query, params)
                candidate_rows = await cur.fetchall()

        # 3. Post-Process and Pre-Rank Candidates
        candidates: List[CandidateMatch] = []
        weight = config["bidirectional_weight"]

        for row in candidate_rows:
            cos_dist = float(row["cosine_distance"])
            cos_sim = max(0.0, 1.0 - cos_dist)

            rev_cos_dist = float(row["reverse_cosine_distance"]) if row.get("reverse_cosine_distance") is not None else None
            rev_cos_sim = max(0.0, 1.0 - rev_cos_dist) if rev_cos_dist is not None else None

            # Calculate combined bidirectional score for pre-ranking
            if rev_cos_sim is not None:
                combined_score = (1.0 - weight) * cos_sim + weight * rev_cos_sim
            else:
                combined_score = cos_sim

            if combined_score < config["min_similarity_threshold"]:
                continue

            candidates.append(CandidateMatch(
                user_id=UUID(str(row["user_id"])),
                age=row.get("age"),
                gender=row.get("gender"),
                orientation=row.get("orientation"),
                relationship_goal=row.get("relationship_goal"),
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
                distance_km=round(row["distance_km"], 1) if row.get("distance_km") is not None else None,
                profile=row.get("profile") or {},
                cosine_distance=round(cos_dist, 4),
                cosine_similarity=round(cos_sim, 4),
                reverse_cosine_distance=round(rev_cos_dist, 4) if rev_cos_dist is not None else None,
                reverse_cosine_similarity=round(rev_cos_sim, 4) if rev_cos_sim is not None else None,
                combined_score=round(combined_score, 4)
            ))

        # Sort descending by combined score
        candidates.sort(key=lambda c: c.combined_score, reverse=True)

        # Slice to pre_rank_limit for Stage 2 Pairwise Reasoning
        pre_ranked_candidates = candidates[:config["pre_rank_limit"]]
        logger.info(
            f"Stage 1 Recall for user {user_id}: Retrieved {len(candidate_rows)} pool candidates, "
            f"pre-ranked top {len(pre_ranked_candidates)} (limit={config['pre_rank_limit']})."
        )
        return pre_ranked_candidates
