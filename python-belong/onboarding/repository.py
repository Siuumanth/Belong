import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from psycopg.rows import dict_row
from db.connection import get_db_connection

class OnboardingRepository:
    @staticmethod
    async def create_conversation(user_id: UUID, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    INSERT INTO conversations (user_id, state, status)
                    VALUES (%s, %s, 'active')
                    RETURNING id, user_id, state, status, created_at, updated_at;
                """
                await cur.execute(query, (str(user_id), json.dumps(initial_state)))
                row = await cur.fetchone()
                await conn.commit()
                return dict(row)

    @staticmethod
    async def get_conversation(conversation_id: UUID) -> Optional[Dict[str, Any]]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                query = """
                    SELECT id, user_id, state, status, created_at, updated_at
                    FROM conversations
                    WHERE id = %s;
                """
                await cur.execute(query, (str(conversation_id),))
                row = await cur.fetchone()
                if not row:
                    return None
                return dict(row)

    @staticmethod
    async def update_conversation_state(
        conversation_id: UUID,
        state: Dict[str, Any],
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        async with get_db_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                if status:
                    query = """
                        UPDATE conversations
                        SET state = %s, status = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id, user_id, state, status, created_at, updated_at;
                    """
                    await cur.execute(query, (json.dumps(state), status, str(conversation_id)))
                else:
                    query = """
                        UPDATE conversations
                        SET state = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id, user_id, state, status, created_at, updated_at;
                    """
                    await cur.execute(query, (json.dumps(state), str(conversation_id)))
                
                row = await cur.fetchone()
                await conn.commit()
                if not row:
                    return None
                return dict(row)

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
