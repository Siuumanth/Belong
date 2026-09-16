from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from embeddings.service import EmbeddingService
from profile.repository import ProfileRepository

router = APIRouter(tags=["embeddings"])
embedding_service = EmbeddingService()

class EmbeddingGenerateResponse(BaseModel):
    user_id: UUID
    self_text: str
    wants_text: str
    self_embedding_length: int
    wants_embedding_length: int
    status: str

@router.post(
    "/profiles/{user_id}/embeddings",
    response_model=EmbeddingGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate canonical semantic embeddings for a profile",
)
async def generate_profile_embeddings(user_id: UUID):
    try:
        result = await embedding_service.generate_and_store_embeddings(user_id)
        return EmbeddingGenerateResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}",
        )

@router.get(
    "/profiles/{user_id}/embeddings",
    summary="Fetch embedding status and canonical source text for a profile",
)
async def get_profile_embedding_status(user_id: UUID):
    profile = await ProfileRepository.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    # Fetch source text from DB
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
