import logging
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from profile.repository import ProfileRepository
from profile.models import StructuredProfileJSON
from embeddings.serializer import CanonicalSerializer
from embeddings.client import EmbeddingClient

logger = logging.getLogger(__name__)

# embedding worker
class EmbeddingService:
    """Orchestrates serialization, vector embedding generation, and database updates."""

    def __init__(self, serializer: Optional[CanonicalSerializer] = None, client: Optional[EmbeddingClient] = None):
        self.serializer = serializer or CanonicalSerializer()
        self.client = client or EmbeddingClient()

    async def generate_and_store_embeddings(self, user_id: UUID) -> Dict[str, Any]:
        """Fetches profile, computes canonical text, generates vectors, and persists to DB."""
        profile_response = await ProfileRepository.get_profile(user_id)
        if not profile_response:
            raise ValueError(f"Profile for user_id {user_id} not found.")

        profile_dict = profile_response.profile or {}
        
        # Serialize profile into self_text and wants_text
        self_text, wants_text = self.serializer.serialize(profile_dict)

        # Generate vectors
        self_vec, wants_vec = await self.client.embed_batch([self_text, wants_text])

        source_text = {
            "self_text": self_text,
            "wants_text": wants_text,
            "serializer_version": "v1_canonical",
            "model_name": self.client.model_name
        }

        # Update database
        success = await ProfileRepository.update_profile_embeddings(
            user_id=user_id,
            self_embedding=self_vec,
            wants_embedding=wants_vec,
            embedding_source_text=source_text,
        )

        if not success:
            raise RuntimeError(f"Failed to persist embeddings for user_id {user_id}.")

        logger.info(f"Successfully generated and persisted embeddings for user_id {user_id}")
        return {
            "user_id": str(user_id),
            "self_text": self_text,
            "wants_text": wants_text,
            "self_embedding_length": len(self_vec),
            "wants_embedding_length": len(wants_vec),
            "status": "completed",
        }
