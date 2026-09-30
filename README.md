# Belong

A backend matchmaking system that evaluates relationship compatibility using conversational AI onboarding, structured trait extraction, and a 2-stage vector + LLM matching pipeline.

---

# Dependencies

- **Backend Services:** Go (Gateway & Auth Service), Python 3.12 (FastAPI API server & Worker process)
- **AI & Graph Frameworks:** LangGraph, LangChain, Groq API (`openai/gpt-oss-120b`), Hugging Face / local `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Database:** PostgreSQL 16 + `pgvector` extension
- **Messaging:** RabbitMQ (AMQP) for asynchronous task queues
- **Containerization:** Docker & Docker Compose
- **Testing:** Custom multi-user simulation suite (`httpx` + `asyncio`)

---

## 1. System Overview

Belong evaluates whether two people's emotional needs, lifestyle preferences, and relationship goals align. Instead of matching purely on shared hobbies or numeric trait ratings, it looks for **complementary patterns** (e.g., *User A seeks a reassuring partner* $\leftrightarrow$ *User B naturally provides supportive listening*).

![](https://github.com/Siuumanth/Belong/blob/main/images/architecure.png?raw=true)

### Key Components:
1. **Conversational Onboarding:** A 6-question AI-guided dialogue that dynamically asks follow-up probes if an answer is vague or incomplete.
2. **Evidence-Grounded Extraction:** Parses user responses into a multi-dimensional JSON schema, storing verbatim quotes as evidence and keeping unknown fields `null`.
3. **Async Embeddings Generation:** Computes dual semantic vector representations (`self` vs. `wants`) in background RabbitMQ workers.
4. **2-Stage Match Pipeline:** Fast SQL + `pgvector` filtering (Stage 1), followed by detailed pairwise LLM compatibility reasoning (Stage 2).

---

## 2. Architecture & Service Boundaries

### System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Web / Mobile Client                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Requests
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Go API Gateway (Port 9000)                      │
│                  (CORS, Token Verification, Routing)                   │
└───────────┬────────────────────────────────────────────────┬───────────┘
            │                                                │
            ▼                                                ▼
┌───────────────────────┐                        ┌───────────────────────┐
│  Go Auth Service      │                        │  Belong API (FastAPI) │
│  (Port 9001)          │                        │  (Port 8000)          │
│  - User Reg & Auth    │                        │  - Profile Management │
│  - JWT Generation     │                        │  - Onboarding Graph   │
└───────────┬───────────┘                        │  - Job Dispatcher     │
            │                                    └───────────┬───────────┘
            ▼                                                │
┌───────────────────────┐                                    │ Publish Jobs
│  Auth Database (Postgres)                                  ▼
└───────────────────────┘                        ┌───────────────────────┐
                                                 │   RabbitMQ Broker     │
                                                 │   ├── embedding_jobs  │
                                                 │   └── matching_jobs   │
                                                 └───────────┬───────────┘
                                                             │
                                        ┌────────────────────┴────────────────────┐
                                        │ Consume Queues                          │
                                        ▼                                         ▼
                            ┌───────────────────────┐                 ┌───────────────────────┐
                            │  Embedding Worker     │                 │  Matching Worker      │
                            │  (worker_embedding.py)│                 │  (worker_matching.py) │
                            │  - SentenceTransf.    │                 │  - Stage 1 pgvector   │
                            │  - Generates 384d Vec │                 │  - Stage 2 LLM Agent  │
                            └───────────┬───────────┘                 └───────────┬───────────┘
                                        │                                         │
                                        └────────────────────┬────────────────────┘
                                                             │ DB Read/Write
                                                             ▼
                                                ┌──────────────────────────┐
                                                │  PostgreSQL + pgvector   │
                                                │  - profiles              │
                                                │  - match_jobs            │
                                                │  - compatibility_results │
                                                └──────────────────────────┘
```

### Service Breakdown

* **`gateway` (Go):** Single entry point on port 9000. Forwards authenticated `/api/...` traffic to internal microservices.
* **`auth` (Go):** Manages user registration, bcrypt password hashing, and JWT token issuance.
* **`belong-api` (FastAPI):** Handles profile updates, executes the LangGraph onboarding flow, and queues background jobs.
* **`belong-workers` (Python):** Background worker container running dedicated queue listeners:
  - `embedding_jobs`: Serializes profiles and generates semantic vector embeddings.
  - `matching_jobs`: Runs Stage 1 retrieval and Stage 2 pairwise LLM evaluation.
* **`belong-postgres`:** PostgreSQL storage holding profiles, vectors, conversations, and persisted match reports.
* **`belong-rabbitmq`:** AMQP message broker managing background execution tasks.

---

## 3. Onboarding & Signal Extraction Flow

The onboarding system separates **gathering user input** from **extracting psychographic evidence**:

```text
 ┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
 │  User Response Text  │ ────►  │  LLM Trait Extractor │ ────►  │ Psychographic Profile│
 └──────────────────────┘        └──────────────────────┘        │ (Lifestyle, Values,  │
                                            │                    │  Interests, Needs)   │
                                            ▼                    └──────────────────────┘
                                 ┌──────────────────────┐
                                 │   Coverage Policy    │
                                 │ Evaluates completeness│
                                 └──────────┬───────────┘
                                            │
                                  Vague?    │   Clear?
                             ┌──────────────┴──────────────┐
                             ▼                             ▼
                ┌─────────────────────────┐   ┌─────────────────────────┐
                │ Generate Contextual     │   │ Advance to Next         │
                │ Follow-up Probe Question│   │ Onboarding Question     │
                └─────────────────────────┘   └─────────────────────────┘
```

### Extraction Principles:
- **Hint-Based Extraction:** Target dimensions serve as hints, not rigid restrictions. If a user describes lifestyle habits and personal values in a single answer, both dimensions are extracted.
- **Dual-Filing Rule:** Explicit dealbreakers (e.g., "must be non-smoker", "monogamy only") are saved exclusively into `constraints.dealbreakers` and omitted from general preference fields.
- **Evidence Traceability:** Claims include verbatim quotes from user responses, ensuring predictions are grounded in real inputs.

---

## 4. Two-Stage Matchmaking Pipeline

To scale matching efficiently without sending every candidate pair to expensive LLM calls, Belong uses a two-stage pipeline:

```text
[ Incoming Match Request ]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 1: SQL Filtering & pgvector Similarity           │
│ - Filter hard constraints (gender, age, location, dealbreakers)│
│ - Compute cosine distance on self_embedding vs wants_embedding │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼ Top Candidate Shortlist (K)
┌────────────────────────────────────────────────────────┐
│ STAGE 2: Pairwise LLM Compatibility Reasoning          │
│ - Evaluate reciprocal alignment (User A Needs ↔ User B)│
│ - Evaluate complementary traits (User B Needs ↔ User A)│
│ - Assign dimensional verdicts & overall score          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
[ Persist Results to PostgreSQL & Return Job Complete ]
```

### Stage 1: Retrieval (SQL + `pgvector`)
- Filters candidates by hard constraints: age range, distance radius, gender, and hard dealbreakers.
- Computes vector similarity between User A's `wants_embedding` and User B's `self_embedding` using `pgvector` HNSW indexes.

### Stage 2: Reasoning (Pairwise LLM Agent)
- Direct LLM execution with strict JSON output validation (no complex tool-calling dependency wrappers).
- Evaluates bi-directional alignment across key areas (`relationship_expectations`, `communication_style`, `conflict_resolution`, `lifestyle`).
- Outputs detailed verdicts (`strong_alignment`, `partial`, `unclear`, `conflict`) along with evidence mappings.

---

## 5. Async Worker Choreography

All long-running tasks (vector embedding generation and match evaluations) are fully asynchronous.

```text
Client                  FastAPI (belong-api)              RabbitMQ               Worker (belong-workers)           PostgreSQL
  │                              │                           │                              │                           │
  ├─ POST /matches ─────────────►│                           │                              │                           │
  │                              ├─ Create Job (pending) ────┼──────────────────────────────┼──────────────────────────►│
  │                              │                           │                              │                           │
  │                              ├─ Publish matching_job ───►│                              │                           │
  │◄─ 202 Accepted (job_id) ─────┤                           │                              │                           │
  │                              │                           ├─ Consume matching_job ──────►│                           │
  │                              │                           │                              ├─ Execute Stage 1 & 2      │
  │                              │                           │                              ├─ Write Results & Status ─►│
  │                              │                           │                              │  (status = 'completed')   │
  │                              │                           │                              │                           │
  ├─ GET /matches/jobs/{id} ────►│                           │                              │                           │
  │◄─ 200 OK (status: completed)─┴───────────────────────────┴──────────────────────────────┴──────────────────────────►│
```

---

## 6. Database Design & Schema

Database constraints and relational schemas are defined in PostgreSQL 16.

![](https://github.com/Siuumanth/Belong/blob/main/images/schema.png?raw=true)

```text
┌────────────────────────────────────────────────────────┐
│                        profiles                        │
├────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                          │
│ user_id (UUID, FK -> users.id)                         │
│ gender, age, location (POINT)                          │
│ profile_data (JSONB - Psychographic Dimensions)        │
│ self_embedding (VECTOR(384))                           │
│ wants_embedding (VECTOR(384))                          │
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
│ dimension_results (JSONB)                              │
│ reciprocal_alignments (JSONB)                          │
│ evidence_mappings (JSONB)                              │
└────────────────────────────────────────────────────────┘
```

---

## 7. Local Setup & Container Deployment

### Prerequisites
- Docker & Docker Compose installed

### Running the System
```powershell
# Build and start all services (API, Auth, Gateway, Workers, Postgres, RabbitMQ)
docker compose up -d --build
```

### Running Simulations & Integration Tests
```powershell
# Execute the end-to-end multi-persona simulator
cd tests
python run_custom_simulation.py
```