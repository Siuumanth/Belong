import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from psycopg.rows import dict_row
from db.connection import get_db_connection
from profile.models import ProfileCreate, ProfileUpdate, ProfileResponse

class ProfileRepository:
    @staticmethod
    async def create_profile(data: ProfileCreate) -> ProfileResponse:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    INSERT INTO profiles (
                        user_id, name, age, gender, orientation, latitude, longitude,
                        relationship_goal, preferred_age_min, preferred_age_max,
                        max_distance_km, preferred_genders, required_relationship_goal,
                        profile
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s
                    )
                    RETURNING user_id, name, age, gender, orientation, latitude, longitude,
                              relationship_goal, preferred_age_min, preferred_age_max,
                              max_distance_km, preferred_genders, required_relationship_goal,
                              profile, extraction_version, created_at, updated_at;
                """
                await cur.execute(
                    query,
                    (
                        str(data.user_id),
                        data.name,
                        data.age,
                        data.gender,
                        data.orientation,
                        data.latitude,
                        data.longitude,
                        data.relationship_goal,
                        data.preferred_age_min,
                        data.preferred_age_max,
                        data.max_distance_km,
                        json.dumps(data.preferred_genders),
                        data.required_relationship_goal,
                        json.dumps(data.profile),
                    ),
                )
                row = await cur.fetchone()
                await conn.commit()
                return ProfileResponse(**row)

    @staticmethod
    async def get_profile(user_id: UUID) -> Optional[ProfileResponse]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT user_id, name, age, gender, orientation, latitude, longitude,
                           relationship_goal, preferred_age_min, preferred_age_max,
                           max_distance_km, preferred_genders, required_relationship_goal,
                           profile, extraction_version, created_at, updated_at
                    FROM profiles
                    WHERE user_id = %s;
                """
                await cur.execute(query, (str(user_id),))
                row = await cur.fetchone()
                if not row:
                    return None
                return ProfileResponse(**row)

    @staticmethod
    async def update_profile(user_id: UUID, patch: ProfileUpdate) -> Optional[ProfileResponse]:
        updates = []
        values = []
        
        # Explicit field mapping
        fields = [
            ("name", patch.name),
            ("age", patch.age),
            ("gender", patch.gender),
            ("orientation", patch.orientation),
            ("latitude", patch.latitude),
            ("longitude", patch.longitude),
            ("relationship_goal", patch.relationship_goal),
            ("preferred_age_min", patch.preferred_age_min),
            ("preferred_age_max", patch.preferred_age_max),
            ("max_distance_km", patch.max_distance_km),
            ("required_relationship_goal", patch.required_relationship_goal),
        ]
        
        for col, val in fields:
            if val is not None:
                updates.append(f"{col} = %s")
                values.append(val)

        if patch.preferred_genders is not None:
            updates.append("preferred_genders = %s")
            values.append(json.dumps(patch.preferred_genders))

        if patch.profile is not None:
            updates.append("profile = %s")
            values.append(json.dumps(patch.profile))

        if not updates:
            return await ProfileRepository.get_profile(user_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(str(user_id))

        set_clause = ", ".join(updates)
        query = f"""
            UPDATE profiles
            SET {set_clause}
            WHERE user_id = %s
            RETURNING user_id, name, age, gender, orientation, latitude, longitude,
                      relationship_goal, preferred_age_min, preferred_age_max,
                      max_distance_km, preferred_genders, required_relationship_goal,
                      profile, extraction_version, created_at, updated_at;
        """

        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, tuple(values))
                row = await cur.fetchone()
                await conn.commit()
                if not row:
                    return None
                return ProfileResponse(**row)


    @staticmethod
    async def update_profile_embeddings(
        user_id: UUID,
        self_embedding: List[float],
        wants_embedding: List[float],
        embedding_source_text: Dict[str, Any],
    ) -> bool:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                self_vec_str = json.dumps(self_embedding)
                wants_vec_str = json.dumps(wants_embedding)
                source_text_str = json.dumps(embedding_source_text)

                query = """
                    UPDATE profiles
                    SET self_embedding = %s::vector,
                        wants_embedding = %s::vector,
                        embedding_source_text = %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s;
                """
                await cur.execute(query, (self_vec_str, wants_vec_str, source_text_str, str(user_id)))
                await conn.commit()
                return cur.rowcount > 0

