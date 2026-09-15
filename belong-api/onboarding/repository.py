import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from psycopg.rows import dict_row
from db.connection import get_db_connection

class OnboardingRepository:
    @staticmethod
    async def create_conversation(user_id: UUID, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        state = initial_state or {}
        status = state.get("status", "active")
        current_area_index = state.get("current_area_index", 0)
        follow_up_count = state.get("follow_up_count", 0)
        covered_areas = json.dumps(state.get("covered_areas", []))
        extracted_signals = json.dumps(state.get("extracted_signals", {}))

        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    INSERT INTO conversations (user_id, status, current_area_index, follow_up_count, covered_areas, extracted_signals)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, status, current_area_index, follow_up_count, covered_areas, extracted_signals, created_at, updated_at;
                """
                await cur.execute(query, (str(user_id), status, current_area_index, follow_up_count, covered_areas, extracted_signals))
                row = await cur.fetchone()
                await conn.commit()
                res = dict(row)
                if isinstance(res.get("covered_areas"), str):
                    res["covered_areas"] = json.loads(res["covered_areas"])
                if isinstance(res.get("extracted_signals"), str):
                    res["extracted_signals"] = json.loads(res["extracted_signals"])
                return res

    @staticmethod
    async def get_conversation(conversation_id: UUID) -> Optional[Dict[str, Any]]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, user_id, status, current_area_index, follow_up_count, covered_areas, extracted_signals, created_at, updated_at
                    FROM conversations
                    WHERE id = %s;
                """
                await cur.execute(query, (str(conversation_id),))
                row = await cur.fetchone()
                if not row:
                    return None
                res = dict(row)
                if isinstance(res.get("covered_areas"), str):
                    res["covered_areas"] = json.loads(res["covered_areas"])
                if isinstance(res.get("extracted_signals"), str):
                    res["extracted_signals"] = json.loads(res["extracted_signals"])
                return res

    @staticmethod
    async def update_conversation_state(
        conversation_id: UUID,
        state: Dict[str, Any],
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        status_val = status or state.get("status", "active")
        current_area_index = state.get("current_area_index", 0)
        follow_up_count = state.get("follow_up_count", 0)
        covered_areas = state.get("covered_areas", [])
        extracted_signals = state.get("extracted_signals", {})

        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    UPDATE conversations
                    SET status = %s,
                        current_area_index = %s,
                        follow_up_count = %s,
                        covered_areas = %s,
                        extracted_signals = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, user_id, status, current_area_index, follow_up_count, covered_areas, extracted_signals, created_at, updated_at;
                """
                await cur.execute(query, (
                    status_val,
                    current_area_index,
                    follow_up_count,
                    json.dumps(covered_areas),
                    json.dumps(extracted_signals),
                    str(conversation_id)
                ))
                row = await cur.fetchone()
                await conn.commit()
                if not row:
                    return None
                res = dict(row)
                if isinstance(res.get("covered_areas"), str):
                    res["covered_areas"] = json.loads(res["covered_areas"])
                if isinstance(res.get("extracted_signals"), str):
                    res["extracted_signals"] = json.loads(res["extracted_signals"])
                return res

    @staticmethod
    async def add_message(
        conversation_id: UUID,
        role: str,
        content: str,
        question_id: Optional[str] = None
    ) -> Dict[str, Any]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    INSERT INTO conversation_messages (conversation_id, role, content, question_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, conversation_id, role, content, question_id, created_at;
                """
                await cur.execute(query, (str(conversation_id), role, content, question_id))
                row = await cur.fetchone()
                await conn.commit()
                return dict(row)

    @staticmethod
    async def get_messages(conversation_id: UUID) -> List[Dict[str, Any]]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, conversation_id, role, content, question_id, created_at
                    FROM conversation_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC;
                """
                await cur.execute(query, (str(conversation_id),))
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
