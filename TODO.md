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
- [x] **Phase 6: Async Matching Worker Engine (RabbitMQ + belong-workers)**
- [x] **Phase 7: Matching Stage 1 — SQL Filters & pgvector Retrieval**
- [x] **Phase 8: Matching Stage 2 — Pairwise Compatibility Reasoning Agent**
- [x] **Phase 9: Go API Gateway Routing & Full Proxy Integration**
- [ ] **Phase 10: Synthetic Evaluation, Benchmarking & End-to-End Testing**

---

### Phase 5: Deterministic Semantic Serialization & In-Process Embeddings ✅
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
- [x] Wire automatic in-process background task upon onboarding completion in `belong-api/api/routes/onboarding.py`.
- [x] Expose `POST /api/profiles/{user_id}/embeddings` and `GET /api/profiles/{user_id}/embeddings` endpoints.

---

### Phase 7: Matching Stage 1 — SQL Filters & pgvector Retrieval ✅
- [x] Implement deterministic SQL hard filters in `belong-api/matching/retrieval.py`:
  - [x] Gender and orientation matching (mutual compatibility).
  - [x] Mutual age range checks (`preferred_age_min` / `preferred_age_max`).
  - [x] Haversine distance calculation using `latitude` and `longitude` (`max_distance_km`).
  - [x] Relationship goal compatibility.
- [x] Implement pgvector nearest-neighbor search:
  - [x] Cosine distance query: `user_a.wants_embedding <=> candidate.self_embedding`.
  - [x] Configurable candidate pool retrieval limit (`MATCHING_CANDIDATE_POOL_LIMIT`, default 50).
- [x] Implement configurable pre-ranking & candidate reduction:
  - [x] Weighted bidirectional scoring (`MATCHING_BIDIRECTIONAL_WEIGHT`).
  - [x] Narrow shortlist to top N candidates (`MATCHING_PRE_RANK_LIMIT`, default 15) for deep LLM reasoning.
  - [x] Configurable via `RetrievalOptions` and environment variables in `belong-api/config.py`.

---

### Phase 6: Async Matching Worker Engine (RabbitMQ + belong-workers) ✅
- [x] Wire up RabbitMQ in `docker-compose.yml` (uncomment `rabbitmq` service).
- [x] Implement RabbitMQ connection manager in `belong-workers/rabbitmq/connection.py` (aio-pika).
- [x] Implement message consumer + job dispatcher in `belong-workers/rabbitmq/consumer.py`:
  - [x] Route `belong.matching` queue jobs to `MatchingWorker`.
  - [x] Route `belong.embedding` queue jobs to `EmbeddingWorker`.
  - [x] Atomic DB status tracking in `jobs` table (`running`, `completed`, `failed`).
- [x] Implement **Matching Worker** in `belong-workers/workers/matching_worker.py`:
  - [x] Stage 1 (SQL filters + pgvector retrieval) → Stage 2 (pairwise LLM reasoning) → write compatibility results to Postgres.
  - [x] Update job status in `jobs` table → `completed`.
- [x] Add RabbitMQ publisher to `belong-api` for dispatching matching jobs (`POST /api/matches`).
- [x] Implement PostgreSQL fallback reconciler loop in `belong-workers/main.py` for picking up unacknowledged `pending` jobs.

---

### Phase 8: Matching Stage 2 — Pairwise Compatibility Reasoning Agent ✅
- [x] Define compatibility structured output schema in `belong-api/matching/schemas.py` & `belong-workers/matching/schemas.py`:
  - [x] Categorical verdicts: `strong_alignment`, `partial_alignment`, `unclear`, `conflict`.
  - [x] Dimension results: `emotional_needs`, `core_values`, `lifestyle`, `conflict_style`.
  - [x] Evidence arrays: `evidence_a`, `evidence_b`.
  - [x] Lists for `strong_alignments`, `potential_conflicts`, `dealbreaker_violations`, `uncertainties`.
- [x] Implement pairwise reasoning prompt & LangGraph Agent in `belong-workers/matching/compatibility.py`:
  - [x] Groq LLM client backend (`LLM_PROVIDER="groq"`, model `llama-3.3-70b-versatile`).
  - [x] Configurable prompt template `PAIRWISE_REASONING_PROMPT_TEMPLATE`.
  - [x] Bidirectional evaluation & anti-hallucination evidence quote requirement.
- [x] Implement multi-dimensional deterministic ranking algorithm in `belong-workers/matching/ranking.py`.
- [x] Persist results into `compatibility_results` table.
- [x] Implement matching API endpoints in `belong-api/api/routes/matches.py`:
  - [x] `POST /api/matches` — enqueue matching job (auth-derived user_id, returns HTTP 202 Accepted with `job_id`).
  - [x] `GET /api/matches/jobs/{job_id}` — poll status details for matching job.
  - [x] `GET /api/matches/{user_id}` — fetch latest persisted qualitative matches for user.

---

### Phase 9: Go API Gateway & Auth Integration ✅
- [x] Integrate Go Auth service into monorepo (`/auth`) and update `go.work` workspace.
- [x] Configure Gateway reverse proxy routes:
  - [x] Forward `/auth/*` to Go Auth service (`AUTH_SERVICE_URL`, default `:9001`).
  - [x] Forward `/profiles/*` to `belong-api` (`BELONG_SERVICE_URL`, default `:8000`).
  - [x] Forward `/onboarding/*` to `belong-api`.
  - [x] Forward `/matches/*` to `belong-api`.
  - [x] Forward `/api/*` prefix stripped to `belong-api`.
- [x] Implement JWT authentication verification and claim injection (`X-User-ID`, `X-Auth-Expires`, `X-Request-ID`).
- [x] Implement circuit breaker, rate limiting, and structured logging in Gateway.
- [x] Add gateway health probe check checking `belong-api` and Auth service readiness in `gateway/internal/health/healthcheck.go`.

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

Final:
- [ ] Make embeddings update when profile is updated