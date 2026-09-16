# Belong — Global Development Roadmap & TODO List

**Project:** Belong — AI-Assisted Compatibility Matchmaking Platform  
**Stack:** Go API Gateway + `belong-api` (FastAPI) + `belong-workers` (RabbitMQ consumers) + PostgreSQL 16 / pgvector + Hugging Face Embeddings + LLM Reasoning Agents

---

## Progress Overview
- [x] **Phase 1: Foundation, Architecture & Scaffolding**
- [x] **Phase 2: Database Schema, pgvector & Migrations**
- [x] **Phase 3: Python Backend Core & Profile CRUD**
- [x] **Phase 4: Conversational Onboarding Engine (LangGraph)**
- [x] **Phase 5: Deterministic Semantic Serialization & Embeddings**

---

### Phase 5: Deterministic Semantic Serialization & Embeddings ✅
- [x] Implement **Canonical Semantic Serializer** in `belong-api/embeddings/serializer.py`:
  - [x] Category field-based serialization for `SELF TEXT` and `WANTS TEXT`.
  - [x] Omit empty categories and filter low-confidence extractions (`confidence < 0.5`).
  - [x] Strip evidence quotes, question IDs, and metadata from embedding text.
- [x] Build Hugging Face / Local embedding client in `belong-api/embeddings/client.py`:
  - [x] Async batch client for `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
  - [x] Offline fallback vector generator for resilience when offline or without HF API key.
- [x] Connect embedding generator to database updates:
  - [x] Store generated vectors in `profiles.self_embedding` and `profiles.wants_embedding`.
  - [x] Persist canonical source text in `profiles.embedding_source_text`.
- [x] Expose `POST /api/profiles/{user_id}/embeddings` and `GET /api/profiles/{user_id}/embeddings` endpoints.

- [ ] **Phase 6: Async Worker Engine (RabbitMQ + belong-workers)**
- [ ] **Phase 7: Matching Stage 1 — SQL Filters & pgvector Retrieval**
- [ ] **Phase 8: Matching Stage 2 — Pairwise Compatibility Reasoning Agent**
- [ ] **Phase 9: Go API Gateway Routing & Full Proxy Integration**
- [ ] **Phase 10: Synthetic Evaluation, Benchmarking & End-to-End Testing**

---

## Detailed Task Breakdown

### Phase 1: Foundation, Architecture & Scaffolding
- [x] Study and freeze core system design (`Belong_MVP_System_Design.md`).
- [x] Create project modular structure:
  - [x] `/gateway` (Go API Gateway with Chi, JWT, Prometheus metrics, Zap logger, Circuit Breaker).
  - [x] `/belong-api` (Modular Python layout: `api/`, `profile/`, `onboarding/`, `embeddings/`, `matching/`, `jobs/`, `db/`).
  - [x] `/belong-workers` (Worker service layout: `workers/`, `rabbitmq/`, `db/`).
  - [x] `/docs` (Centralized documentation).
  - [x] `/scripts` (Verification and operational utilities).
- [x] Establish documentation:
  - [x] [`docs/Belong_MVP_System_Design.md`](file:///d:/code/Golang/Belong/docs/Belong_MVP_System_Design.md) (Master system design).
  - [x] [`docs/retrieval_and_matchmaking_flow.md`](file:///d:/code/Golang/Belong/docs/retrieval_and_matchmaking_flow.md) (Recall vs. compatibility & deterministic serialization architecture).
  - [x] [`docs/onboarding_and_storage_flow.md`](file:///d:/code/Golang/Belong/docs/onboarding_and_storage_flow.md) (Dialogue agent, evidence traceability, and persistence pipeline).
  - [x] [`openapi.yaml`](file:///d:/code/Golang/Belong/openapi.yaml) (OpenAPI 3.1.0 complete API specification).
  - [x] [`docs/api_list.md`](file:///d:/code/Golang/Belong/docs/api_list.md) (API endpoint reference table and short usage guide).

### Phase 2: Database Infrastructure & Migrations (Section 11)
- [x] Configure [`docker-compose.yml`](file:///d:/code/Golang/Belong/docker-compose.yml) with PostgreSQL 16 and `pgvector` enabled (`pgvector/pgvector:pg16`).
- [x] Mount migrations directory directly into `/docker-entrypoint-initdb.d` for automatic bootstrapping.
- [x] Write SQL migration scripts according to Section 11 specifications:
  - [x] `001_init_extensions.sql` (enables `vector`, `uuid-ossp`, `pgcrypto`).
  - [x] `002_create_profiles.sql` (deterministic SQL columns, `profile JSONB`, `self_embedding VECTOR(384)`, `wants_embedding VECTOR(384)`, HNSW cosine indexes, filtering indexes).
  - [x] `003_create_conversations.sql` (`conversations` and `conversation_messages` with cascade deletes and indexes).
  - [x] `004_create_jobs.sql` (`jobs` queue with `idx_jobs_claim` index for `SKIP LOCKED` worker claiming).
  - [x] `005_create_compatibility_results.sql` (`compatibility_results` table with multi-dimensional JSONB verdicts and unique pair constraint).
- [x] Implement database connection pool (`connection.py`) with `psycopg_pool`.
- [x] Implement programmatic migration runner script (`migrate.py`).
- [x] Create automated environment startup and database verification scripts:
  - [x] [`start.ps1`](file:///d:/code/Golang/Belong/start.ps1) and [`start.bat`](file:///d:/code/Golang/Belong/start.bat).
  - [x] [`scripts/verify_db.ps1`](file:///d:/code/Golang/Belong/scripts/verify_db.ps1) and [`scripts/verify_db.sql`](file:///d:/code/Golang/Belong/scripts/verify_db.sql).

---

### Phase 3: Python Backend Core & Profile CRUD ✅
- [x] Implement Pydantic data schemas in `belong-api/profile/models.py`:
  - [x] Structured profile sub-models (`SelfProfile`, `WantsProfile`, `ConstraintsProfile`).
  - [x] Evidence model (`label`, `summary`, `quote`, `question_id`, `confidence`).
  - [x] Profile create, update, and read DTOs.
- [x] Implement database repository in `belong-api/profile/repository.py`:
  - [x] `create_profile(user_id, data)`
  - [x] `get_profile(user_id)`
  - [x] `update_profile(user_id, patch_data)`
- [x] Implement FastAPI endpoints in `belong-api/api/routes/profiles.py`:
  - [x] `POST /api/profiles` — create profile.
  - [x] `GET /api/profiles/{user_id}` — fetch full structured profile.
  - [x] `PATCH /api/profiles/{user_id}` — partial profile update.

---

### Phase 4: Conversational Onboarding Engine (LangGraph) ✅
- [x] Global configuration module (`belong-api/config.py`) with 6 question definitions, LLM settings, and extraction target dimensions.
- [x] Define onboarding state schema (`OnboardingState`) in `belong-api/onboarding/state.py`.
- [x] Implement LangGraph workflow nodes in `belong-api/onboarding/graph.py`:
  - [x] Signal extractor node with strict evidence quote extraction.
  - [x] Vagueness check node (triggers adaptive follow-up only when answer is too vague).
  - [x] Warm conversational response generator node (acknowledges user, transitions naturally).
  - [x] Profile finalizer (auto-saves structured profile to DB on completion).
- [x] Implement onboarding API endpoints in `belong-api/api/routes/onboarding.py`:
  - [x] `POST /api/onboarding/session` — initiate conversation.
  - [x] `POST /api/onboarding/message` — advance dialogue step.
  - [x] `GET /api/onboarding/{conversation_id}` — fetch dialogue transcript & state.

---



### Phase 6: Async Worker Engine (RabbitMQ + belong-workers)
- [ ] Wire up RabbitMQ in `docker-compose.yml` (uncomment `rabbitmq` service).
- [ ] Implement RabbitMQ connection manager in `belong-workers/rabbitmq/connection.py` (aio-pika).
- [ ] Implement message consumer + job dispatcher in `belong-workers/rabbitmq/consumer.py`:
  - [ ] Route by `routing_key`: `embedding` → `EmbeddingWorker`, `matching` → `MatchingWorker`.
  - [ ] Ack on success, Nack+requeue on recoverable errors.
- [ ] Implement **Embedding Worker** in `belong-workers/workers/embedding_worker.py`:
  - [ ] Read profile from Postgres → run serializer → call Hugging Face → write vectors back.
  - [ ] Update job status → `completed`.
- [ ] Add RabbitMQ publisher to `belong-api` for dispatching jobs after onboarding completes.
- [ ] Implement retry policy with exponential backoff and error logging.

---

### Phase 7: Matching Stage 1 — SQL Filters & pgvector Retrieval
- [ ] Implement deterministic SQL hard filters in `belong-api/matching/retrieval.py`:
  - [ ] Gender and orientation matching.
  - [ ] Mutual age range checks (`preferred_age_min` / `preferred_age_max`).
  - [ ] Haversine distance calculation using `latitude` and `longitude` (`max_distance_km`).
  - [ ] Relationship goal compatibility.
- [ ] Implement pgvector nearest-neighbor search:
  - [ ] Cosine distance query: `user_a.wants_embedding <=> candidate.self_embedding`.
  - [ ] Retrieve candidate shortlist (top 50–100 candidates).
- [ ] Implement cheap pre-ranking / candidate reduction:
  - [ ] Narrow shortlist to top 10–20 candidates for deep LLM reasoning.
- [ ] Implement **Matching Worker** in `belong-workers/workers/matching_worker.py`.

---

### Phase 8: Matching Stage 2 — Pairwise Compatibility Reasoning Agent
- [ ] Define compatibility structured output schema in `belong-api/matching/schemas.py`:
  - [ ] Categorical verdicts: `strong_alignment`, `partial_alignment`, `unclear`, `conflict`.
  - [ ] Dimension results: `emotional_needs`, `core_values`, `lifestyle`, `conflict_style`.
  - [ ] Evidence arrays: `evidence_a`, `evidence_b`.
  - [ ] Lists for `strong_alignments`, `potential_conflicts`, `dealbreaker_violations`, `uncertainties`.
- [ ] Implement pairwise reasoning prompt in `belong-api/matching/compatibility.py`:
  - [ ] Bidirectional evaluation: `A wants → B provides` AND `B wants → A provides`.
  - [ ] Anti-hallucination instruction: quote evidence from both profiles.
- [ ] Implement multi-dimensional ranking algorithm in `belong-api/matching/ranking.py`.
- [ ] Persist results into `compatibility_results` table.
- [ ] Implement matching API endpoints in `belong-api/api/routes/matches.py`:
  - [ ] `POST /api/matches` — enqueue matching job (returns HTTP 202 Accepted with `job_id`).
  - [ ] `GET /api/matches/jobs/{job_id}` — poll job status and retrieve results once completed.
  - [ ] `GET /api/matches/{user_id}` — fetch latest persisted matches for user.

---

### Phase 9: Go API Gateway & Auth Integration
- [x] Integrate Go Auth service into monorepo (`/auth`) and update `go.work` workspace.
- [x] Configure Gateway reverse proxy routes:
  - [x] Forward `/auth/*` to Go Auth service (`AUTH_SERVICE_URL`, default `:9001`).
  - [x] Forward `/profiles/*` to `belong-api` (`BELONG_SERVICE_URL`, default `:8000`).
  - [x] Forward `/onboarding/*` to `belong-api`.
  - [x] Forward `/matches/*` to `belong-api`.
  - [x] Forward `/api/*` prefix stripped to `belong-api`.
- [x] Implement JWT authentication verification and claim injection (`X-User-ID`, `X-Auth-Expires`, `X-Request-ID`).
- [x] Implement circuit breaker, rate limiting, and structured logging in Gateway.
- [ ] Add gateway health probe check checking `belong-api` and Auth service readiness.

---

### Phase 10: Synthetic Evaluation, Benchmarking & End-to-End Testing
- [ ] Create synthetic test persona library (`tests/fixtures/personas.json`):
  - [ ] Complementary Pairs (Expected: Strong Alignment).
  - [ ] Shared Interests with Conflict Clashes (Expected: Recall success, Reasoning conflict).
  - [ ] Hard Dealbreaker Violations (Expected: Immediate exclusion).
  - [ ] Vague / Incomplete Profiles (Expected: Uncertainty verdicts).
- [ ] Evaluate candidate recall quality (`Recall@50` and `Recall@100`).
- [ ] Evaluate Compatibility Reasoning Agent consistency and quote faithfulness.
- [ ] Run full end-to-end flow test (Onboarding → Embeddings → Matching Job → Polling Results).
