# Belong — Backend Matchmaking Engine for Serious Relationships

> **A decoupled microservice matchmaking system that evaluates long-term relationship compatibility using conversational AI onboarding, psychographic trait extraction, fast dual-vector similarity recall (`pgvector`), and deep pairwise LLM reasoning.**

---

## 💡 Why Belong?

### 💔 The Problem with Modern Dating Apps
- **Superficial Sorting:** Split-second visual decisions based on photos and prompt quips instead of real compatibility.
- **Swipe Fatigue & Ghosting:** Infinite swiping creates burnout and disposable interactions rather than genuine human connection.
- **Surface Similarity vs. Real Compatibility:** Liking the same music or hobbies does not mean two people share core values, emotional needs, or relationship goals.

### ❤️ How Belong Fixes It
- **Emotional Complementarity:** Matches partners based on how they balance each other (e.g., pairing someone needing reassurance with a grounded, supportive listener).
- **Evidence-Based AI Profiling:** Natural conversational onboarding extracts structured psychographic insights backed by verbatim user quotes (`self` vs. `wants`).
- **Mutual Intentionality:** Two-way matching ensures User A fits what User B seeks **and** User B fits what User A seeks.
- **Surface Layer Screening:** Instant baseline filtering (distance, age, gender reciprocity, dealbreakers) before running AI vector evaluations.

---

## 🛠️ Tech Stack & Dependencies

- **Backend Microservices:** Go 1.22+ (API Gateway & Auth Service), Python 3.12 (FastAPI API Server & Worker Process)
- **AI & Graph Frameworks:** LangGraph, LangChain, Groq API (`openai/gpt-oss-120b`), Hugging Face / local `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Database:** PostgreSQL 16 + `pgvector` extension (HNSW vector indexes)
- **Messaging:** RabbitMQ (AMQP) for asynchronous task queues
- **Containerization:** Docker & Docker Compose
- **Testing:** Custom multi-user simulation & benchmark suite (`httpx` + `asyncio`)

---

## 1. System Overview & Architecture

Belong's backend is built with a decoupled, asynchronous microservice architecture designed for high throughput, sub-15ms candidate retrieval, and scalable background reasoning.

![Belong Architecture](images/architecure.png)
*(Fallback GitHub Link: `https://github.com/Siuumanth/Belong/blob/main/images/architecure.png?raw=true`)*

### Service Boundaries & Architecture Diagram

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
└───────────┬───────────┘                        │  - Candidate Retrieval│
            │                                    │  - Job Dispatcher     │
            ▼                                    └───────────┬───────────┘
┌───────────────────────┐                                    │ Publish Jobs
│  Auth Database        │                                    ▼
│  (PostgreSQL)         │                        ┌───────────────────────┐
└───────────────────────┘                        │   RabbitMQ Broker     │
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
- **`gateway` (Go `:9000`):** Single entry point handling CORS, JWT verification, and proxying to internal services.
- **`auth` (Go `:9001`):** Microservice managing user registration, bcrypt password hashing, and JWT signing.
- **`belong-api` (FastAPI `:8000`):** Handles profile updates, AI onboarding graphs (LangGraph), real-time candidate retrieval (`CandidateRetriever`), and pairwise LLM evaluations.
- **`belong-workers` (Python):** Background worker process executing RabbitMQ queues (`embedding_jobs` and `matching_jobs`).
- **`belong-postgres`:** PostgreSQL 16 storage holding profiles, 384-d `pgvector` indexes, conversations, and persisted match reports.
- **`belong-rabbitmq`:** AMQP message broker managing background execution queues.

---

## 2. Onboarding & Signal Extraction Flow

The onboarding engine separates **user interaction** from **psychographic signal extraction**:

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

### Extraction Principles
- **Conversational Guidance:** A 6-question AI-guided dialogue that dynamically asks follow-up probe questions if an answer is vague or incomplete.
- **Hint-Based Extraction:** Target dimensions act as extraction hints. If a user describes lifestyle habits and personal values in a single answer, both dimensions are extracted simultaneously.
- **Dual-Filing Rule:** Explicit dealbreakers (e.g., "must be a non-smoker", "monogamy only") are saved into `constraints.dealbreakers` and omitted from general trait preferences.
- **Evidence Traceability:** All extracted claims include verbatim quotes from user responses to ground LLM compatibility reasoning in verified facts.

### Data Representation & Embedding Serialization Example

#### 1. Stored Profile Signal JSON (`profiles.profile` in PostgreSQL)
User responses are stored as structured JSON with evidence quotes, confidence scores, and strict separation between `self`, `wants`, and `constraints`:

```json
{
  "self": {
    "values": [
      { "summary": "Values honesty and transparency", "evidence": "I value honesty above all else", "confidence": 0.95 }
    ],
    "emotional_needs": [
      { "summary": "Needs verbal reassurance when stressed", "evidence": "I need reassurance when stressed", "confidence": 0.92 }
    ]
  },
  "wants": {
    "partner_traits": [
      { "summary": "Grounded and patient listener", "evidence": "Looking for a patient partner", "confidence": 0.95 }
    ]
  },
  "constraints": {
    "dealbreakers": [
      { "summary": "Non-smoker only", "evidence": "Cannot date anyone who smokes", "confidence": 1.0 }
    ]
  }
}
```

#### 2. Canonical Text Serialization (`CanonicalSerializer`)
Before vectorization, the `CanonicalSerializer` filters items above confidence threshold ($\ge 0.7$), strips metadata/quotes, and formats canonical text:

* **Generated `self_text`:**
  ```text
  SELF
  Values: Values honesty and transparency.
  Emotional needs: Needs verbal reassurance when stressed.
  ```

* **Generated `wants_text`:**
  ```text
  WANTS
  Partner traits: Grounded and patient listener.
  ```

#### 3. Embedding Vector Generation (`self_embedding` & `wants_embedding`)
Canonical text strings are passed to the embedding model (`all-MiniLM-L6-v2`) to produce 384-dimensional floating point vectors:

```text
self_text  ──► [Embedding Model] ──► self_embedding  (VECTOR(384))
wants_text ──► [Embedding Model] ──► wants_embedding (VECTOR(384))
```

These vectors are saved directly into the PostgreSQL `profiles` table for fast `pgvector` HNSW cosine similarity search (`wants_embedding <=> self_embedding`).

---

## 3. Two-Stage Matchmaking Pipeline

To scale matching efficiently without running expensive LLM evaluations on millions of candidate pairs, Belong uses a **two-stage pipeline**:

```text
[ Incoming Match Request ]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ STAGE 1: Surface Layer SQL & pgvector Cosine Recall    │
│ - Surface Layer: Filter gender, age, distance, dealbreakers│
│ - Vector Search: Cosine similarity on self vs wants    │
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
[ Persist Results to PostgreSQL & Return Qualitative Analysis ]
```

### Stage 1: Fast Retrieval (Surface Layer SQL + `pgvector`)
- Applies hard surface layer constraints: age range, distance radius (Haversine), gender preference, and dealbreakers.
- Computes vector similarity between User A's `wants_embedding` and Candidate B's `self_embedding`.
- Returns candidate previews in **5ms to 15ms** without consuming LLM tokens.

### Stage 2: Deep Reasoning (Pairwise LLM Agent)
- Evaluates bi-directional alignment across **4 core relationship dimensions**:
  1. **Emotional Needs:** Support mechanisms, stress handling, and reassurance dynamics.
  2. **Core Values:** Principles regarding family, ambition, personal growth, and ethics.
  3. **Lifestyle & Routine:** Daily habits, social battery, work-life balance, and schedules.
  4. **Conflict & Communication:** How partners navigate disagreements, process emotions, and handle space.
- Outputs qualitative verdicts (`strong_alignment`, `partial`, `unclear`, `conflict`) along with evidence mappings.

---

## 4. System Execution Flows

Belong supports two decoupled execution models depending on the workflow:

### Flow A: Real-Time Candidate Retrieval & On-Demand LLM Reasoning
Instant candidate preview search (~5-15ms) followed by on-demand deep LLM analysis when requested by the user:

```text
1. Fast Candidate Retrieval:
   Client ──► Go Gateway (:9000) ──► Belong API ──► SQL + pgvector ──► Previews (~5-15ms)

2. On-Demand Deep Reasoning:
   Client ──► Go Gateway (:9000) ──► Belong API ──► Pairwise LLM Agent ──► Detailed Report
```

### Flow B: Asynchronous Queue Mode (Background Worker)
For long-running batch operations or decoupled background job processing via RabbitMQ:

```text
Client                  FastAPI (belong-api)              RabbitMQ               Worker (belong-workers)           PostgreSQL
  │                              │                           │                              │                           │
  ├─ POST /matches ─────────────►│                           │                              │                           │
  │                              ├─ Publish matching_job ───►│                              │                           │
  │◄─ 202 Accepted (job_id) ─────┤                           ├─ Consume matching_job ──────►│                           │
  │                              │                           │                              ├─ Execute Stage 1 & 2      │
  │                              │                           │                              ├─ Write Results to DB ────►│
  │                              │                           │                              │                           │
  ├─ GET /matches/jobs/{id} ────►│                           │                              │                           │
  │◄─ 200 OK (status: completed)─┴───────────────────────────┴──────────────────────────────┴──────────────────────────►│
```

---

## 5. Database Schema & Storage

Database constraints and relational schemas are defined in PostgreSQL 16 using `pgvector`.

![Database Schema](images/schema.png)
*(Fallback GitHub Link: `https://github.com/Siuumanth/Belong/blob/main/images/schema.png?raw=true`)*

```text
┌────────────────────────────────────────────────────────┐
│                        profiles                        │
├────────────────────────────────────────────────────────┤
│ user_id (UUID, PK)                                     │
│ name (TEXT), age (INT), gender (TEXT)                  │
│ orientation (TEXT), relationship_goal (TEXT)           │
│ latitude (DOUBLE PRECISION), longitude (DOUBLE)        │
│ preferred_age_min (INT), preferred_age_max (INT)      │
│ max_distance_km (INT), preferred_genders (JSONB)       │
│ profile (JSONB - Psychographic Dimensions)             │
│ self_embedding (VECTOR(384))                           │
│ wants_embedding (VECTOR(384))                          │
│ created_at, updated_at (TIMESTAMPTZ)                   │
└────────────────────────────────────────────────────────┘
                           │
                           │ 1:N
                           ▼
┌────────────────────────────────────────────────────────┐
│                 compatibility_results                  │
├────────────────────────────────────────────────────────┤
│ id (UUID, PK)                                          │
│ user_a_id (UUID, FK -> profiles.user_id)               │
│ user_b_id (UUID, FK -> profiles.user_id)               │
│ overall_verdict (VARCHAR)                              │
│ compatibility_score (FLOAT)                            │
│ dimension_results (JSONB)                              │
│ reciprocal_alignments (JSONB)                          │
│ evidence_mappings (JSONB)                              │
│ is_latest (BOOLEAN)                                    │
│ created_at (TIMESTAMPTZ)                               │
└────────────────────────────────────────────────────────┘
```

---

## 6. API Endpoint Summary

| Category | Endpoint | Method | Stage / Mode | Description & Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Match Retrieval** | `/matches/candidates/{user_id}` | `GET` | Stage 1 (Real-Time) | Instant candidate retrieval via SQL surface filters + `pgvector` (~5-15ms). **No LLM used**. |
| **Match Retrieval** | `/matches/candidates` | `POST` | Stage 1 (Real-Time) | Candidate retrieval with options in request body. **No LLM used**. |
| **Deep Analysis** | `/matches/analyze` | `POST` | Stage 2 (On-Demand) | Runs pairwise LLM compatibility reasoning on a selected candidate and saves results. |
| **Deep Analysis** | `/matches/analyze/{candidate_id}` | `POST` | Stage 2 (On-Demand) | Path-parameter variant for on-demand candidate LLM reasoning. |
| **Match Results** | `/matches/details/pair/{candidate_id}` | `GET` | Query | Retrieves saved qualitative compatibility breakdown for a candidate pair. |
| **Match Results** | `/matches/{user_id}` | `GET` | Query | Retrieves all latest saved compatibility evaluations for a user. |
| **Async Jobs** | `/matches` | `POST` | Async Queue | Submits background matching job to RabbitMQ queue. Returns `202 Accepted` with `job_id`. |
| **Async Jobs** | `/matches/jobs/{job_id}` | `GET` | Query | Checks status (`pending`, `completed`, `failed`) of an async background job. |
| **Onboarding** | `/onboarding/chat` | `POST` | Onboarding | Advances the LangGraph AI onboarding conversation and extracts profile signals. |
| **Authentication** | `/auth/register`, `/auth/login` | `POST` | Auth | User registration, password hashing, and JWT token issuance via Go Auth service. |

---

## 7. Local Setup & Container Deployment

### Prerequisites
- Docker & Docker Compose installed

### Running the Complete Stack
```powershell
# Build and start all microservices (Gateway, Auth, API, Workers, Postgres, RabbitMQ)
docker compose up -d --build
```

### Verification & Health Check
```powershell
# Test Gateway routing on Port 9000
curl http://localhost:9000/health
```

### Running Multi-User Simulation Suite
```powershell
# Execute the end-to-end multi-persona simulation script
cd tests
python run_custom_simulation.py
```