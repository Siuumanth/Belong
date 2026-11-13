# 01. Overall System Architecture

> **Belong — AI-Assisted Compatibility Matchmaking Platform**  
> *"Relationships Over Swiping: Matching on emotional and psychological complementarity, not superficial photo feeds."*

---

## 1. What is Belong? What Problem Does It Solve?

### The Problem with Modern Dating Apps
Modern dating platforms (Tinder, Bumble, Hinge) are structured like visual slot machines:
1. **Superficial Swiping & Split-Second Judgments:** Users make decisions in <500ms based on curated photos and witty one-liners.
2. **Surface Similarity vs. Psychological Complementarity:** Liking the same band, hiking, or favorite food has zero correlation with relationship longevity. What matters is emotional support dynamics, conflict resolution styles, life pace, and core values.
3. **Swipe Fatigue & Asymmetric Liquidity:** Infinite browsing creates choice paralysis, burnout, and disposable interactions rather than intentional commitment.
4. **Unidirectional Matching:** Most algorithms match by clustering similar users without verifying whether **User A fulfills what User B actually needs AND vice versa**.

### Belong’s Core Thesis
Belong is a **compatibility-driven matchmaking engine for serious, long-term relationships**.
* **Evidence-Grounded AI Onboarding:** Users don't fill out dry, biased forms. They have a natural conversation with an adaptive AI guide. The guide extracts psychological traits, values, and relationship needs, grounding every signal in **verbatim user quotes**.
* **Dual-Aspect Profile Architecture (`SELF` vs. `WANTS`):** Explicitly separates *who the user is* (`SELF`) from *what the user needs in a partner* (`WANTS`).
* **Two-Way Reciprocal Matching:** A match is valid **only** if:
  $$\text{User A fulfills User B's WANTS} \quad \text{AND} \quad \text{User B fulfills User A's WANTS}$$
* **Two-Stage Matchmaking Pipeline:** Fast vector-accelerated candidate recall (Stage 1) followed by deep, qualitative pairwise LLM reasoning across 4 core relationship dimensions (Stage 2).

---

## 2. High-Level Architecture & Text Block Diagram

Belong uses a **decoupled, polyglot microservice and event-driven architecture**:

```
+---------------------------------------------------------------------------------+
|                                CLIENT LAYER                                     |
|                       React + TypeScript + Tailwind SPA                         |
+---------------------------------------+-----------------------------------------+
                                        |  HTTP / REST (JSON + JWT)
                                        v
+---------------------------------------------------------------------------------+
|                             API GATEWAY (Go :9000)                              |
|   - Central Entrypoint               - JWT Verification & Claim Extraction      |
|   - Reverse Proxy & Routing          - Request ID & Header Injection            |
|   - Rate Limiting & Circuit Breakers - Unified Health Probing                   |
+-------------------+-------------------------------------+-----------------------+
                    |                                     |
    /auth/*         |                     /profiles/*, /onboarding/*, /matches/*
    (Reverse Proxy) |                     (Injected: X-User-ID, X-Request-ID)
                    v                                     v
+-----------------------+             +-------------------------------------------+
|   AUTH SERVICE (Go)   |             |            BELONG API (FastAPI)           |
|        (:9001)        |             |                  (:8000)                  |
| - Registration/Login  |             | - Conversational Onboarding (LangGraph)   |
| - Password Hashing    |             | - Signal Extraction & Pydantic Validation |
| - JWT Issuance        |             | - Profile CRUD & Settings Management      |
| - Direct DB Access    |             | - Job Dispatcher (RabbitMQ Publisher)     |
+-----------+-----------+             +--------+------------------+---------------+
            |                                  |                  |
            | SQL                              | SQL              | AMQP 0-9-1
            |                                  | (psycopg async)  | (aio-pika)
            v                                  v                  v
+--------------------------------------------------+   +--------------------------+
|           POSTGRESQL 16 + PGVECTOR (:5432)       |   |   RABBITMQ BROKER        |
| - users: Auth credentials & UUIDs                |   |   Exchange: belong.jobs  |
| - profiles: Demographics, JSONB signals, vectors |   |   Queues:                |
| - conversations & conversation_messages          |   |   - belong.embedding     |
| - jobs: Persistent task state & claim locks      |   |   - belong.matching      |
| - compatibility_results & match_runs             |   +------------+-------------+
+--------------------------------------------------+                |
                    ^                                               | AMQP Consumer
                    | Reads profiles / Writes results               v
+-------------------+-------------------------------------------------------------+
|                            BELONG WORKERS (Python)                              |
| - EmbeddingWorker: Canonical serialization -> sentence-transformers (384-dim)   |
| - MatchingWorker:                                                               |
|     * Stage 1: Deterministic SQL hard filters + pgvector bidirectional recall   |
|     * Stage 2: LangGraph Pairwise LLM Compatibility Reasoning (Groq LLaMA 3.3)  |
|     * Deterministic Ranking: (-dealbreakers, verdict, net_alignment, vec_score) |
| - DB Reconciler: Polling fallback with SELECT ... FOR UPDATE SKIP LOCKED        |
+---------------------------------------------------------------------------------+
```

---

## 3. Service Breakdown & Responsibilities

| Service | Language / Stack | Port | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Frontend** | React, TypeScript, Vite, Tailwind | `5173` | UI for conversational onboarding chat, candidate match review, compatibility breakdown cards. |
| **Gateway** | Go, Chi Router, Zap, crypto | `9000` | Single public entry point. Reverse proxies requests, validates JWTs, injects internal headers (`X-User-ID`), enforces rate limiting and CORS. |
| **Auth** | Go, Chi, bcrypt, golang-jwt | `9001` | Manages user credentials, password hashing (bcrypt), and issues HMAC-SHA256 signed JWT tokens. |
| **Belong API** | Python 3.12, FastAPI, Pydantic, LangGraph | `8000` | Orchestrates the multi-turn conversational onboarding graph, extracts semantic signals, saves profiles, exposes query endpoints, enqueues jobs. |
| **Belong Workers** | Python 3.12, aio-pika, psycopg, LangGraph | Background | Asynchronous worker engine: consumes `belong.embedding` and `belong.matching` tasks. Executes Stage 1 pgvector recall and Stage 2 LLM reasoning. |
| **RabbitMQ** | Erlang / RabbitMQ 3.13 | `5672` / `15672` | Message broker decoupling slow AI tasks from client HTTP request lifecycles. |
| **PostgreSQL** | Postgres 16 + `pgvector` extension | `5432` | Relational data, JSONB structured profile signals, HNSW indexes for 384-dimensional cosine similarity search, and job coordination. |

---

## 4. Why Go Gateway + Python FastAPI? (Polyglot Justification)

In an interview, explain why a polyglot microservice architecture is a **deliberate engineering choice**, not accidental complexity:

### Why Go for Gateway & Auth?
1. **Concurrency & Raw Network Throughput:** Go's goroutines have tiny memory overhead (~2KB) compared to Python threads or processes. It can easily handle tens of thousands of idle or concurrent client connections without choking.
2. **CPU Efficiency for Crypto & Proxying:** Password hashing (bcrypt) and cryptographic JWT signature checks (`golang-jwt`) are CPU-bound. Go compiles to native machine code, avoiding Python's Global Interpreter Lock (GIL) and process-spawning overhead.
3. **Low-Latency Reverse Proxying:** Go's standard library `net/http/httputil.ReverseProxy` is battle-tested, zero-allocation friendly, and handles header injection and streaming out of the box.

### Why Python FastAPI for Core API & Workers?
1. **First-Class AI/ML Ecosystem:** The modern AI infrastructure stack (LangChain, LangGraph, Hugging Face, `sentence-transformers`, Groq SDK, PyTorch) is Python-native.
2. **Schema Enforcement with Pydantic:** Pydantic v2 (Rust-backed) provides lightning-fast serialization and strict validation for the complex nested JSON structures that LLMs output.
3. **Unified Async IO (`asyncio`):** FastAPI and `aio-pika` operate smoothly on non-blocking async loops, allowing workers to wait on external LLM network I/O without burning compute resources.

---

## 5. Storage & Messaging Infrastructure Roles

### 1. PostgreSQL 16 + `pgvector`
* **Unified Database:** Instead of operating separate systems for relational metadata (users, profiles) and an external vector database (Pinecone, Weaviate, Milvus), Belong keeps everything in Postgres.
* **ACID Transactions:** Profile data, extraction state, and vector embeddings are committed together in atomic transactions.
* **Hybrid Queries in One Round-Trip:** Hard SQL filters (age, distance, gender preferences) and pgvector semantic distance queries (`<=>`) execute in a single SQL query plan.
* **HNSW Indexing:** Hierarchical Navigable Small World indexes allow logarithmic approximate nearest neighbor (ANN) vector lookups over 384-dimensional embeddings.

### 2. RabbitMQ Message Broker
* **Decoupling Latencies:**
  * Client HTTP request budget: **< 100 ms**.
  * Embedding generation: **~200 ms - 1 s**.
  * Pairwise LLM reasoning across 15 candidates: **5 s - 25 s**.
  If done synchronously inside the HTTP handler, connections would time out, thread pools would exhaust, and users would experience horrible latency.
* **Traffic Buffering & Spikes:** During peak onboarding spikes, RabbitMQ safely absorbs messages without dropping tasks, feeding them to workers based on worker capacity (`prefetch_count`).
* **Work Distribution:** Distributes tasks across multiple worker replicas seamlessly.

---

## 6. Synchronous vs. Asynchronous Operations

Understanding which flows are synchronous and which are asynchronous demonstrates real-world distributed systems knowledge:

```
+----------------------------------+----------------------------------+
|      SYNCHRONOUS FLOWS           |       ASYNCHRONOUS FLOWS         |
|  (Client waits for response)     |   (Fire-and-forget / Background) |
+----------------------------------+----------------------------------+
| 1. User Register & Login         | 1. Vector Embedding Generation   |
|    Client -> Gateway -> Auth     |    Triggered on onboarding finish|
|                                  |    Published to belong.embedding |
| 2. Onboarding Dialogue Turn      |                                  |
|    Client -> Gateway -> API      | 2. Stage 1 SQL & pgvector Recall |
|    (Invokes LangGraph turn,      |    Worker fetches top candidates |
|     returns conversational reply)|                                  |
|                                  | 3. Stage 2 Pairwise LLM Analysis |
| 3. Profile Fetching & Editing    |    Worker evaluates 15 pairs     |
|                                  |    via Groq LLaMA-3.3-70B        |
| 4. Polling Job Status            |                                  |
|    GET /api/matches/jobs/{id}    | 4. Database Job Reconciler Loop  |
|    Returns 'running'/'completed' |    Recovers lost/pending jobs    |
+----------------------------------+----------------------------------+
```

---

## 7. Service-to-Service Communication Flow

1. **Client to Gateway:** Standard HTTPS with JSON payload. Authenticated routes carry `Authorization: Bearer <token>`.
2. **Gateway to Downstream Services:**
   * Gateway strips unnecessary prefixes (e.g., `/auth/login` $\rightarrow$ `/login` on Auth service; `/api/profiles` $\rightarrow$ `/profiles` on Belong API).
   * Gateway decodes and validates JWT signature.
   * Gateway injects verified identity headers:
     * `X-User-ID`: Validated UUID string of the authenticated user.
     * `X-Auth-Expires`: Unix timestamp of token expiration.
     * `X-Request-ID`: Distributed tracing UUID for correlating logs across services.
   * Downstream services (Belong API) **never re-parse JWTs**; they trust the sanitized `X-User-ID` header injected by the internal gateway.
3. **API to Workers via RabbitMQ:**
   * Uses AMQP 0-9-1.
   * Messages are published to topic/direct exchange `belong.jobs` with routing keys:
     * `embedding`: routed to queue `belong.embedding`.
     * `matching`: routed to queue `belong.matching`.
   * Payloads are compact JSON documents containing `{ "job_id": "...", "user_id": "...", "type": "..." }`.

---

## 8. Why This Architecture Instead of a Monolith?

Interviewers frequently ask: *"Why didn't you just build one big Django or FastAPI monolith?"*

### 1. Resource Footprint & Scaling Characteristics
* **Gateway/Auth:** High network I/O, low CPU, low memory. Needs horizontal scaling based on request rate.
* **Belong API:** Moderate CPU, high I/O (database, LangGraph conversational LLM calls).
* **Workers:** High memory (if loading PyTorch/sentence-transformers in-memory) and high CPU/GPU demand.
In a monolith, scaling the web server to handle more HTTP requests also duplicates heavy ML dependencies across all instances, causing massive memory bloat.

### 2. Independent Failure Domains
* If the LLM provider (Groq) experiences an outage or rate limits during candidate reasoning, the worker gracefully fails or retries in the background. **The core API and Gateway remain 100% responsive.** Users can still log in, read profiles, and chat with the onboarding bot.
* In a monolith, background worker crashes or memory leaks (e.g., PyTorch CUDA OOM) can easily take down the HTTP server serving user logins.

### 3. Polyglot Language Advantages
* Go is superior for high-concurrency network proxies, connection pooling, and JWT cryptographic verification.
* Python is unmatched for AI graph orchestration, prompt engineering, and embeddings.

---

## 9. Interview Whiteboard Cheatsheet (Draw & Explain in 2 Minutes)

When an interviewer says: *"Can you draw the architecture of Belong on the whiteboard and explain how it works?"* — this section gives you the exact **visual layout**, **drawing sequence**, and **word-for-word verbal script** to deliver a confident 2-minute pitch.

---

### 🎨 The Whiteboard Diagram (Reproduce This From Memory)

```
                            [ CLIENT (React SPA) ]
                                      |
                                      | HTTP + JWT
                                      v
                        +----------------------------+
                        |   1. GO GATEWAY (:9000)    |
                        | - JWT Verify & Rate Limit  |
                        | - Injects X-User-ID header |
                        +--------------+-------------+
                                       |
                 +---------------------+---------------------+
                 | /auth/* (Public)                          | /profiles, /onboarding, /matches
                 v                                           v
    +------------------------+                  +-------------------------+
    |   2. GO AUTH (:9001)   |                  |  3. BELONG API (:8000)  |
    | - Password Hash (bcrypt|                  | - LangGraph Onboarding  |
    | - Issues HMAC-SHA256   |                  | - Signal Extraction     |
    +-----------+------------+                  | - Job Dispatcher        |
                |                               +------------+------------+
                | SQL                                        |
                |                                            | AMQP Publish
                |                                            v
                |                               +-------------------------+
                |                               |  4. RABBITMQ (:5672)    |
                |                               | - belong.embedding      |
                |                               | - belong.matching       |
                |                               +------------+------------+
                |                                            |
                |                                            | Consume (Prefetch=1)
                v                                            v
+-----------------------------------------------+   +-------------------------+
|        6. POSTGRESQL 16 + PGVECTOR (:5432)    |   |    5. PYTHON WORKERS    |
| - users & conversations                       |<--| - sentence-transformers |
| - profiles (JSONB signals + 384-dim HNSW)     |   | - Stage 1 pgvector      |
| - jobs (Atomic SKIP LOCKED reconciler)        |-->| - Stage 2 Groq LLM      |
| - compatibility_results & match_runs          |   +------------+------------+
+-----------------------------------------------+                |
                                                                 | HTTPS
                                                                 v
                                                        [ GROQ LLaMA-3.3-70B ]
```

---

### ⏱️ Step-by-Step Drawing & Speaking Guide (Chronological)

#### 0:00 – 0:30 | The Edge Layer (Gateway & Auth)
* **What you draw:**
  1. Box at top: `Client (React)`.
  2. Box below it: `Go API Gateway (:9000)`.
  3. Arrow down-left to: `Go Auth (:9001)`.
  4. Arrow down-right to: `Belong API (FastAPI :8000)`.
* **What you say:**
  > *"Belong is an AI compatibility matchmaking platform. All client traffic hits a high-concurrency **Go API Gateway** at port 9000.*  
  > *The Gateway acts as our secure perimeter: it handles rate limiting, CORS, and verifies JWT tokens at the edge.*  
  > *For unauthenticated routes like login and registration, it proxies directly to a lightweight **Go Auth service** using bcrypt and HMAC-SHA256.*  
  > *For protected application routes, the Gateway verifies the token, strips untrusted client headers, and injects a sanitized `X-User-ID` header before reverse-proxying downstream to our Python backend."*

---

#### 0:30 – 1:00 | The AI Core & Database (FastAPI & Postgres)
* **What you draw:**
  1. Box at bottom-left: `Postgres 16 + pgvector (:5432)`.
  2. Connect Auth to Postgres with an arrow.
  3. Connect Belong API to Postgres with an arrow.
  4. Annotate inside Postgres: `profiles (JSONB + 384-dim vector)`.
* **What you say:**
  > *"Our core backend, **Belong API**, is written in FastAPI. It orchestrates our multi-turn conversational onboarding using **LangGraph**.*  
  > *Instead of asking users to swipe on photos, the AI guide converses with them to extract psychological signals into two distinct representations: who the user is (`SELF`), and what they need in a partner (`WANTS`).*  
  > *Everything is persisted in a single **PostgreSQL 16** database with the `pgvector` extension.*  
  > *We use `JSONB` for flexible semi-structured psychological traits, and store two 384-dimensional dense vectors with **HNSW cosine indexes** for fast approximate nearest-neighbor search."*

---

#### 1:00 – 1:30 | Decoupling & Background Workers (RabbitMQ)
* **What you draw:**
  1. Box between API and Worker: `RabbitMQ (:5672)`. Arrow from Belong API $\rightarrow$ RabbitMQ.
  2. Box at bottom-right: `Python Workers`. Arrow from RabbitMQ $\rightarrow$ Python Workers.
  3. Arrow from Workers to external cloud: `Groq LLaMA-3.3-70B`.
* **What you say:**
  > *"Because vector generation and deep LLM reasoning are computationally expensive, we decouple them completely from the user-facing HTTP lifecycle.*  
  > *When onboarding completes or a user requests matches, the API creates a job record in Postgres and publishes an event to **RabbitMQ**.*  
  > *Our asynchronous **Python Workers** consume jobs with `prefetch_count=1` so tasks are distributed fairly without starving any worker."*

---

#### 1:30 – 2:00 | The Two-Stage Matching Pipeline & Close
* **What you draw:**
  1. Bi-directional arrows between `Python Workers` and `Postgres`.
  2. Label the two arrows: `1. Stage 1 SQL + pgvector recall` and `2. Stage 2 Write compatibility results`.
* **What you say:**
  > *"The worker executes a **Two-Stage Matching Pipeline**.*  
  > *In **Stage 1 (Recall)**, it runs a single optimized SQL query combining hard demographic filters—like mutual age, gender, and Haversine distance—with bidirectional `pgvector` cosine distance queries. This narrows 10,000+ candidates down to the top 15 in under 20 milliseconds at zero cost.*  
  > *In **Stage 2 (Reasoning)**, the worker takes those 15 candidates and invokes **Groq LLaMA-3.3-70B** to evaluate pairwise compatibility across 4 core relationship dimensions: emotional needs, core values, lifestyle, and conflict style. We require verbatim quotes from both users' chat transcripts to eliminate hallucinations.*  
  > *The worker ranks them deterministically and writes the results to `compatibility_results`, which the client then polls and displays."*

---

### 💡 3 Sticky Whiteboard Annotations (Draw These for Bonus Points!)

1. **Beside Gateway:** Write `Edge Security` $\rightarrow$ *"Single point of JWT validation; downstream microservices never re-parse tokens."*
2. **Beside pgvector:** Write `<=> (Cosine Distance)` $\rightarrow$ *"Bidirectional matching: User A wants $\leftrightarrow$ User B self AND vice versa."*
3. **Beside Workers/Postgres:** Write `SKIP LOCKED Reconciler` $\rightarrow$ *"Fail-safe recovery loop: if RabbitMQ ever drops a message, the worker claims pending DB jobs atomically."*

