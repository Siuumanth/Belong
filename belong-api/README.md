# Belong Python Service

Modular Python service powering Belong's onboarding, embedding generation, semantic retrieval, and LLM-assisted compatibility reasoning.

## Architecture
- `api/`: FastAPI routes + request/response models.
- `profile/`: Profile CRUD, validation, and domain logic.
- `onboarding/`: Conversational onboarding agent (LangGraph workflow).
- `embeddings/`: Semantic text synthesis and Hugging Face embedding client.
- `matching/`: Hard SQL constraints + pgvector retrieval (`retrieval.py`), pairwise compatibility reasoning agent (`compatibility.py`), and multi-dimensional ranking (`ranking.py`).
- `jobs/`: Durable job creation, atomic claiming (`SKIP LOCKED`), and status updates.
- `db/`: Connection pool, query repositories, and SQL migrations (`db/migrations/`).

## Migrations
The SQL migrations in `db/migrations/` correspond to Section 11 of `Belong_MVP_System_Design.md`:
- `001_init_extensions.sql`: Enables `uuid-ossp`, `pgcrypto`, and `vector` (pgvector).
- `002_create_profiles.sql`: Profiles table, latitude/longitude, profile JSONB, `self_embedding` and `wants_embedding` (VECTOR(384)), and HNSW cosine similarity indexes.
- `003_create_conversations.sql`: Onboarding conversation state and conversation messages.
- `004_create_jobs.sql`: Async matching and embedding job queue with indexes for worker claiming.
- `005_create_compatibility_results.sql`: Multi-dimensional pairwise compatibility verdicts, strong alignments, conflicts, and uncertainties.
