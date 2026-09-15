# TODO Phase 5: Embedding Worker
#
# Flow:
#   message: {"job_id": "...", "user_id": "...", "type": "embedding"}
#     1. Read profile JSON from postgres (profiles table)
#     2. Run deterministic semantic serializer → self_text, wants_text
#     3. Call Hugging Face Embedding API (sentence-transformers/all-MiniLM-L6-v2)
#     4. Write VECTOR(384) back to profiles.self_embedding / wants_embedding
#     5. Persist embedding_source_text debug info
#     6. Update job status → "completed"
