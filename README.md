# Belong

An AI-native Relationship Matchmaking & Deep Compatibility Engine that replaces shallow swipes with dynamic conversational onboarding, structured psychographic profile extraction, and a 2-stage vector + LLM pairwise compatibility reasoning engine.

---

# Dependencies

- **Language & Core Backend:** Python 3.12+, FastAPI, Uvicorn, AsyncIO, Pydantic v2, Go (Golang for Gateway & Auth)
- **AI Orchestration & Agents:** LangGraph (State Graph workflow), LangChain, Groq API (`openai/gpt-oss-120b`), OpenAI Embeddings (`text-embedding-3-small`)
- **Database & Vector Search:** PostgreSQL 16, `pgvector` extension, SQLModel / SQLAlchemy
- **Messaging & Event-Driven Workers:** RabbitMQ (AMQP), Pika, Asynchronous Background Workers (`belong-workers`)
- **Authentication & Gateway:** API Gateway (Port 9000), JWT token validation, Bcrypt
- **Containerization & Deployment:** Docker, Docker Compose
- **Testing & Simulation Framework:** Custom Async Multi-Agent Persona Simulator (`httpx`)

---

## 1. System Overview

Most dating platforms optimize for surface-level similarity or high swipe volume, which is a poor proxy for long-term compatibility. **Belong** evaluates whether two individuals' **emotional needs, behavioral patterns, and relationship expectations are complementary** — even if their surface-level interests differ.

![](https://github.com/Siuumanth/Belong/raw/main/docs/images/system-architecture.png)

### Key Architectural Pillars:
1. **Conversational AI Onboarding:** Replaces static forms with an adaptive 6-question dialogue powered by a LangGraph state machine.
2. **Evidence-Grounded Signal Extraction:** Extracts structured psychographic traits into a multi-dimensional schema, preserving verbatim quotes and confidence scores while leaving unknown fields null.
3. **Event-Driven Embeddings Generation:** Asynchronously computes dual vector embeddings (`self` vs. `wants`) via RabbitMQ worker queues.
4. **2-Stage Hybrid Compatibility Engine:** Uses PostgreSQL `pgvector` + hard SQL filters for rapid candidate shortlist retrieval (Stage 1), followed by deep pairwise LLM reasoning (Stage 2).

---

## 2. Architecture & Service Boundaries

### High-Level Microservices Architecture

```text
                        Clients / Simulator
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │  API Gateway (Go)     │ Port 9000
                     │  Routing, Auth, CORS  │
                     └───────────┬───────────┘
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
    Auth Service (Go)                        belong-api (FastAPI)
    ├── User Registration                    ├── Profile Management
    ├── JWT Issuance                         ├── Onboarding (LangGraph)
    └── Auth Database                        └── Job Queueing
                                                     │
                                                     ▼
                                                 RabbitMQ
                                                /        \
                                               ▼          ▼
                                       Embedding      Matching
                                        Worker         Worker
                                           │              │
                                           └──────┬───────┘
                                                  ▼
                                       PostgreSQL + pgvector
```

### Microservices Responsibilities

* **`gateway` (Go / Port 9000):** Central entry point, route prefixing (`/api/...`), CORS handling, JWT authentication, and request forwarding.
* **`auth` (Go / Port 9001):** Manages user registration, credential hashing (bcrypt), and stateless JWT generation.
* **`belong-api` (Python FastAPI / Port 8000):** Core application server. Manages profile CRUD, orchestrates the multi-turn LangGraph onboarding graph, and dispatches async processing jobs.
* **`belong-workers` (Python):** Event-driven background workers consuming RabbitMQ queues:
  - **`embedding-queue`:** Computes 1536-dimensional `self` and `partner` vector embeddings.
  - **`matching-queue`:** Executes Stage 1 hard SQL filtering + vector similarity search and Stage 2 pairwise LLM compatibility analysis.
* **`belong-postgres`:** PostgreSQL database with `pgvector` extension enabled for high-dimensional vector similarity indexing.
* **`belong-rabbitmq`:** Message broker for asynchronous task distribution and worker decoupling.

---

## 3. Code Architecture & Conversational Onboarding

### Architectural Separation: Evidence vs. Interpretation

```text
                    ┌────────────────────────┐
                    │ Profile Schema Schema  │
                    │ (Psychographic Target) │
                    └───────────┬────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│  Onboarding     │───►│ Evidence Items  │───►│ Coverage Policy      │
│  State Machine  │    │ Raw Text Quotes │    │ Dynamic Probe Decider│
└─────────────────┘    └─────────────────┘    └──────────────────────┘
```

The system strictly decouples evidence collection from interpretation:
- **`OnboardingFlow` (State Graph):** Drives the 6 core dialogue topics (intent, emotional needs, conflict style, lifestyle/values, self-description, dealbreakers) and dynamically triggers up to 2 adaptive probes per topic if answers are vague.
- **`Extractor` (LLM Engine):** Converts raw user statements into a 12+ dimension psychographic model (`lifestyle`, `values`, `interests`, `communication_style`, `conflict_resolution`, `relationship_expectations`, `constraints.dealbreakers`).
- **`CoveragePolicy`:** Evaluates completeness score per topic to determine whether follow-up clarification is needed.

### Key Extraction Principles Enforced

- **Multi-Dimension Extraction:** Target dimensions act as hints rather than strict boundaries. When a user reveals lifestyle habits, values, or interests within a single response, the extractor files them into their respective dimensions simultaneously.
- **Strict Dual-Filing Rule:** Dealbreakers (e.g., "non-smoker", "monogamous only") are routed exclusively into `constraints.dealbreakers` and never duplicated into general values or lifestyle preferences.
- **Zero Hallucination Guarantee:** Extracted claims require verbatim quotes from user inputs. Unknown fields remain `null`.

---

## 4. Two-Stage Matchmaking & Compatibility Engine

Instead of relying solely on vector distance or arbitrary numeric scores, Belong combines rapid candidate retrieval with deep LLM pairwise reasoning.

```text
Stage 1: SQL Hard Filtering + pgvector
  │ (Gender, Age Range, Distance, Dealbreakers, Cosine Distance)
  ▼
Candidate Shortlist (Top-K)
  │
  ▼
Stage 2: Pairwise LLM Compatibility Reasoning
  │ (Reciprocal Analysis: A's Needs ↔ B's Profile & B's Needs ↔ A's Profile)
  ▼
Persisted Compatibility Verdict & Evidence Matrix
```

### Stage 1: Fast Candidate Retrieval (SQL + `pgvector`)
1. **Hard Filtering:** Filters candidate pool by gender preferences, age bounds (`preferred_age_min/max`), geographical radius (`max_distance_km`), and exact dealbreaker matching.
2. **Vector Similarity Search:** Uses cosine distance on `pgvector` HNSW indexes comparing:
   - User A `wants_embedding` $\longleftrightarrow$ User B `self_embedding`
   - User B `wants_embedding` $\longleftrightarrow$ User A `self_embedding`

### Stage 2: Deep Pairwise LLM Reasoning
- **Model-Agnostic Execution:** Directly invokes the LLM (`openai/gpt-oss-120b`) with JSON schema instructions, bypassing fragile model-dependent tool/function calling wrappers.
- **Bi-Directional Reciprocal Analysis:** Evaluates how User A's unexpressed emotional needs match User B's strengths, and vice-versa.
- **Structured Compatibility Breakdown:** Outputs categorical verdicts across key dimensions (`strong_alignment`, `partial`, `unclear`, `conflict`) alongside specific evidence IDs and an overall compatibility synthesis.

---

## 5. Event-Driven Worker Choreography

Matching and embedding generation are fully asynchronous, ensuring API endpoints respond immediately.

### Communication Flow:

1. **Profile Embedding Generation:**
   - User completes profile update / onboarding turn $\rightarrow$ API publishes message to `embedding-queue`.
   - `EmbeddingWorker` calculates vector embeddings via OpenAI API $\rightarrow$ Updates `profiles` table.

2. **Async Match Job Execution:**
   - Client requests matches $\rightarrow$ `belong-api` creates a `match_jobs` record (`status: pending`) and returns HTTP `202 Accepted` with a `job_id`.
   - API publishes `job_id` to `matching-queue`.
   - `MatchingWorker` claims the job $\rightarrow$ Executes Stage 1 SQL/vector retrieval $\rightarrow$ Executes Stage 2 LLM reasoning for shortlisted candidates.
   - Results are written to `compatibility_results` table and `match_jobs` status is updated to `completed`.
   - Client polls `GET /matches/jobs/{job_id}` until completion.

---

## 6. Database Design & Vector Schema

All data integrity and relational constraints are enforced in PostgreSQL 16.

```text
┌────────────────────────────────────────────────────────┐
│                        profiles                        │
├────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                          │
│ user_id (UUID, FK -> users.id)                         │
│ gender, age, location (POINT)                          │
│ profile_data (JSONB - Psychographic Dimensions)        │
│ self_embedding (VECTOR(1536))                          │
│ partner_embedding (VECTOR(1536))                      │
│ created_at, updated_at                                 │
└────────────────────────────────────────────────────────┘
                           │
                           │ 1:N
                           ▼
┌────────────────────────────────────────────────────────┐
│                 compatibility_results                  │
├────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                          │
│ user_a_id (UUID), user_b_id (UUID)                     │
│ overall_verdict (VARCHAR)                              │
│ compatibility_score (FLOAT)                            │
│ dimension_results (JSONB - Categorical Breakdown)      │
│ reciprocal_alignments (JSONB)                          │
│ evidence_mappings (JSONB)                              │
└────────────────────────────────────────────────────────┘
```

---

## 7. Containerization & Deployment

The entire system is containerized with multi-stage Docker builds and orchestrated via Docker Compose.

```powershell
# Build and start all microservices, workers, postgres, and rabbitmq
docker compose up -d --build
```

### Service Health Checks & Order
- `belong-postgres` boots pgvector extension and executes migration scripts in `/db/migrations`.
- `belong-rabbitmq` initiates AMQP broker on port 5672.
- `belong-api` and `belong-workers` wait for PostgreSQL and RabbitMQ health checks to pass before starting application loops.

---

## 8. Simulation & Verification Framework

To test end-to-end multi-user interactions and verify matchmaking quality without manual UI clicks, Belong includes an asynchronous persona simulation suite.

```powershell
# Run synthetic multi-user onboarding & matchmaking simulation
cd tests
python run_custom_simulation.py
```

### What the Simulation Tests:
1. **Demographic Profile Registration:** Registers synthetic test personas (e.g., Alice & Bob).
2. **Multi-Turn Onboarding Dialogue:** Executes multi-turn AI onboarding conversations across all users concurrently.
3. **Async Embedding Generation:** Verifies that RabbitMQ workers compute and persist 1536-dimensional vector embeddings.
4. **Job Polling & Match Verification:** Triggers a match job, polls until `completed`, and fetches persisted compatibility evidence matrix.