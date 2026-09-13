# Belong — Global Development Roadmap & TODO List

**Project:** Belong — AI-Assisted Compatibility Matchmaking Platform  
**Stack:** Go API Gateway + Python Modular Service (FastAPI + Worker) + PostgreSQL 16 / pgvector + Hugging Face Embeddings + LLM Reasoning Agents  

---

## Progress Overview
- [x] **Phase 1: Foundation, Architecture & Scaffolding**
- [x] **Phase 2: Database Schema, pgvector & Migrations**
- [ ] **Phase 3: Python Backend Core & Profile CRUD**
- [ ] **Phase 4: Conversational Onboarding Engine (LangGraph)**
- [ ] **Phase 5: Deterministic Semantic Serialization & Embeddings**
- [ ] **Phase 6: Async Background Job Worker Engine**
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
  - [x] `/python-belong` (Modular Python layout: `api/`, `profile/`, `onboarding/`, `embeddings/`, `matching/`, `jobs/`, `db/`).
  - [x] `/docs` (Centralized documentation).
  - [x] `/scripts` (Verification and operational utilities).
- [x] Establish documentation:
  - [x] [`docs/Belong_MVP_System_Design.md`](file:///d:/code/Golang/Belong/docs/Belong_MVP_System_Design.md) (Master system design).
  - [x] [`docs/retrieval_and_matchmaking_flow.md`](file:///d:/code/Golang/Belong/docs/retrieval_and_matchmaking_flow.md) (Recall vs. compatibility & deterministic serialization architecture).
  - [x] [`docs/onboarding_and_storage_flow.md`](file:///d:/code/Golang/Belong/docs/onboarding_and_storage_flow.md) (Dialogue agent, evidence traceability, and persistence pipeline).
  - [x] [`docs/openapi.yaml`](file:///d:/code/Golang/Belong/docs/openapi.yaml) (OpenAPI 3.1.0 complete API specification).
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

### Phase 3: Python Backend Core & Profile CRUD
- [ ] Implement Pydantic data schemas in `python-belong/profile/models.py`:
  - [ ] Structured profile sub-models (`Self`, `Wants`, `Constraints`, `Contradictions`).
  - [ ] Evidence model (`quote`, `question_id`, `confidence`).
  - [ ] Profile create, update, and read DTOs.
- [ ] Implement database repository in `python-belong/profile/repository.py`:
  - [ ] `create_profile(user_id, data)`
  - [ ] `get_profile_by_user_id(user_id)`
  - [ ] `update_profile(user_id, patch_data)`
- [ ] Implement FastAPI endpoints in `python-belong/api/routes/profiles.py`:
  - [ ] `POST /profiles` — create profile.
  - [ ] `GET /profiles/{user_id}` — fetch full structured profile.
  - [ ] `PATCH /profiles/{user_id}` — partial profile update.
- [ ] Add unit tests for Profile CRUD and validation schemas.

---

### Phase 4: Conversational Onboarding Engine (LangGraph)
- [ ] Define onboarding state schema (`OnboardingState`) in `python-belong/onboarding/state.py`.
- [ ] Formulate the 4–6 core question prompts and guidelines.
- [ ] Implement LangGraph workflow nodes in `python-belong/onboarding/graph.py`:
  - [ ] Next core question selector.
  - [ ] Signal extractor node with strict evidence quote extraction.
  - [ ] Contradiction detector node.
  - [ ] Adaptive follow-up generator with strict guardrail (<= 2 follow-ups limit).
  - [ ] Profile aggregator node (synthesizing dialogue into structured `profile JSONB`).
- [ ] Implement evidence validation guardrail:
  - [ ] Verify that every extracted `evidence.quote` exists verbatim in user input.
- [ ] Implement onboarding API endpoints in `python-belong/api/routes/onboarding.py`:
  - [ ] `POST /onboarding/session` — initiate conversation.
  - [ ] `POST /onboarding/message` — advance dialogue step.
  - [ ] `GET /onboarding/{conversation_id}` — fetch dialogue transcript & state.
- [ ] Trigger automatic profile creation and embedding job dispatch upon onboarding completion.

---

### Phase 5: Deterministic Semantic Serialization & Embeddings
- [ ] Implement the **Deterministic Semantic Serializer** in `python-belong/embeddings/serializer.py`:
  - [ ] Deterministic templates for `SELF TEXT` (what I offer, how I handle conflict, rhythm, values).
  - [ ] Deterministic templates for `WANTS TEXT` (what I need, conflict preferences, lifestyle alignment).
  - [ ] Syntactic pairing alignment check.
- [ ] Build Hugging Face embedding client in `python-belong/embeddings/client.py`:
  - [ ] Asynchronous API client for `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
  - [ ] Batching and rate limit / exponential backoff handling.
- [ ] Connect embedding generator to database updates:
  - [ ] Store generated vectors in `profiles.self_embedding` and `profiles.wants_embedding`.
  - [ ] Persist debug text in `profiles.embedding_source_text`.

---

### Phase 6: Async Background Job Worker Engine
- [ ] Implement database job queue manager in `python-belong/jobs/queue.py`:
  - [ ] `enqueue_job(user_id, job_type, payload)`
  - [ ] `claim_next_job()` with atomic `SELECT ... FOR UPDATE SKIP LOCKED`.
  - [ ] `complete_job(job_id, result)`
  - [ ] `fail_job(job_id, error, retry_allowed)`
- [ ] Build the standalone worker polling loop in `python-belong/jobs/worker.py`:
  - [ ] Worker process lifecycle and graceful shutdown handler.
  - [ ] Dispatcher for `type == 'embedding'` -> calls embedding generator.
  - [ ] Dispatcher for `type == 'matching'` -> calls matching engine.
- [ ] Implement retry policy with exponential backoff and error logging.

---

### Phase 7: Matching Stage 1 — SQL Filters & pgvector Retrieval
- [ ] Implement deterministic SQL hard filters in `python-belong/matching/retrieval.py`:
  - [ ] Gender and orientation matching.
  - [ ] Mutual age range checks (`preferred_age_min` / `preferred_age_max`).
  - [ ] Haversine distance calculation using `latitude` and `longitude` (`max_distance_km`).
  - [ ] Relationship goal compatibility.
- [ ] Implement pgvector nearest-neighbor search:
  - [ ] Cosine distance query: `user_a.wants_embedding <=> candidate.self_embedding`.
  - [ ] Retrieve candidate shortlist (top 50–100 candidates).
- [ ] Implement cheap pre-ranking / candidate reduction:
  - [ ] Narrow shortlist to top 10–20 candidates for deep LLM reasoning.

---

### Phase 8: Matching Stage 2 — Pairwise Compatibility Reasoning Agent
- [ ] Define compatibility structured output schema in `python-belong/matching/schemas.py`:
  - [ ] Categorical verdicts: `strong_alignment`, `partial_alignment`, `unclear`, `conflict`.
  - [ ] Dimension results: `emotional_needs`, `core_values`, `lifestyle`, `conflict_style`.
  - [ ] Evidence arrays: `evidence_a`, `evidence_b`.
  - [ ] Lists for `strong_alignments`, `potential_conflicts`, `dealbreaker_violations`, `uncertainties`.
- [ ] Implement pairwise reasoning prompt in `python-belong/matching/compatibility.py`:
  - [ ] Bidirectional evaluation: `A wants -> B provides` AND `B wants -> A provides`.
  - [ ] Anti-hallucination instruction: quote evidence from both profiles.
- [ ] Implement multi-dimensional ranking algorithm in `python-belong/matching/ranking.py`:
  - [ ] Prioritize candidates with zero dealbreaker violations and verified emotional alignment.
- [ ] Persist results into `compatibility_results` table.
- [ ] Implement matching API endpoints in `python-belong/api/routes/matches.py`:
  - [ ] `POST /matches` — enqueue matching job (returns HTTP 202 Accepted with `job_id`).
  - [ ] `GET /matches/jobs/{job_id}` — poll job status and retrieve results once completed.
  - [ ] `GET /matches/{user_id}` — fetch latest persisted matches for user.

---

### Phase 9: Go API Gateway & Auth Integration
- [x] Integrate Go Auth service into monorepo (`/auth`) and update `go.work` workspace.
- [x] Configure Gateway reverse proxy routes:
  - [x] Forward `/auth/*` to Go Auth service (`AUTH_SERVICE_URL`, default `:9001`).
  - [x] Forward `/profiles/*` to Python service (`BELONG_SERVICE_URL`, default `:8000`).
  - [x] Forward `/onboarding/*` to Python service.
  - [x] Forward `/matches/*` to Python service.
  - [x] Forward `/api/*` prefix stripped to Python service.
- [x] Implement JWT authentication verification and claim injection (`X-User-ID`, `X-Auth-Expires`, `X-Request-ID`).
- [x] Implement circuit breaker, rate limiting, and structured logging in Gateway.
- [ ] Add gateway health probe check checking Python backend and Auth service readiness.

---

### Phase 10: Synthetic Evaluation, Benchmarking & End-to-End Testing
- [ ] Create synthetic test persona library (`tests/fixtures/personas.json`):
  - [ ] Complementary Pairs (Expected: Strong Alignment).
  - [ ] Shared Interests with Conflict Clashes (Expected: Recall success, Reasoning conflict).
  - [ ] Hard Dealbreaker Violations (Expected: Immediate exclusion).
  - [ ] Vague / Incomplete Profiles (Expected: Uncertainty verdicts).
- [ ] Evaluate candidate recall quality (`Recall@50` and `Recall@100`).
- [ ] Evaluate Compatibility Reasoning Agent consistency and quote faithfulness.
- [ ] Run full end-to-end flow test (Onboarding -> Embeddings -> Matching Job -> Polling Results).
