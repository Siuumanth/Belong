import logging
import asyncio
from typing import List, Optional
import httpx
from config import settings

logger = logging.getLogger(__name__)

_local_model_instance = None

def _get_local_model():
    global _local_model_instance
    if _local_model_instance is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = getattr(settings, "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
            logger.info(f"Loading local embedding model: {model_name}")
            _local_model_instance = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers library not installed. Falling back to HTTP/HF provider.")
            _local_model_instance = False
        except Exception as e:
            model_name = getattr(settings, "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
            logger.error(f"Failed to load local model {model_name}: {e}")
            _local_model_instance = False
    return _local_model_instance if _local_model_instance is not False else None


class EmbeddingClient:
    """Async Embedding Client supporting local sentence-transformers inference
    and fallback to Hugging Face Inference API.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        self.dimension = getattr(settings, "EMBEDDING_DIMENSION", 384)

    async def embed_text(self, text: str) -> List[float]:
        """Generates embedding vector for a single text string."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        results = await self.embed_batch([text])
        return results[0] if results else [0.0] * self.dimension

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of text strings."""
        if not texts:
            return []

        # Filter and prepare batch
        cleaned_texts = [t.strip() if t else "" for t in texts]
        non_empty = [t for t in cleaned_texts if t]

        if not non_empty:
            return [[0.0] * self.dimension for _ in texts]

        # Try local model first if configured
        if getattr(settings, "USE_LOCAL_EMBEDDINGS", True):
            model = _get_local_model()
            if model is not None:
                try:
                    loop = asyncio.get_running_loop()
                    embeddings = await loop.run_in_executor(
                        None,
                        lambda: model.encode(cleaned_texts, convert_to_numpy=True).tolist()
                    )
                    return embeddings
                except Exception as e:
                    logger.error(f"Local embedding generation failed: {e}. Trying HTTP fallback.")

        # Fallback to Hugging Face Inference API
        return await self._embed_via_hf_api(cleaned_texts)

    async def _embed_via_hf_api(self, texts: List[str]) -> List[List[float]]:
        """Fallback method to query Hugging Face Feature Extraction API."""
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
        headers = {}
        hf_token = getattr(settings, "HF_API_TOKEN", "")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    api_url,
                    json={"inputs": texts, "options": {"wait_for_model": True}},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                embeddings = []
                for item in data:
                    if isinstance(item, list):
                        if len(item) > 0 and isinstance(item[0], list):
                            seq_len = len(item)
                            dim = len(item[0])
                            pooled = [
                                sum(item[i][d] for i in range(seq_len)) / seq_len
                                for d in range(dim)
                            ]
                            embeddings.append(pooled)
                        else:
                            embeddings.append(item)
                    else:
                        embeddings.append([0.0] * self.dimension)
                return embeddings

            except Exception as e:
                logger.error(f"HF API embedding request failed: {e}")
                return [self._generate_fallback_vector(t) for t in texts]

    def _generate_fallback_vector(self, text: str) -> List[float]:
        """Deterministically generates normalized mock vector from text hash for resilience when offline."""
        import hashlib
        if not text:
            return [0.0] * self.dimension
        
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = []
        for i in range(self.dimension):
            byte_val = digest[i % len(digest)]
            val = ((byte_val / 255.0) * 2.0) - 1.0
            vec.append(val)
        
        norm = sum(x*x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
