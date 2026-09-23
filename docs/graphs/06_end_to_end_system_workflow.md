# End-to-End System Workflow & Architecture

This document presents the complete architectural journey of a user in Belong—from the first conversational onboarding turn to receiving reciprocally verified matchmaking recommendations.

---

## 1. End-to-End System Flowchart

```mermaid
flowchart TD
    subgraph OnboardingPhase ["Phase 1: Conversational Onboarding (belong-api)"]
        User(["User Client"]) -->|POST /api/onboarding/message| OnboardingRoute["Onboarding API Route"]
        OnboardingRoute --> StateDB[(PostgreSQL: conversations)]
        OnboardingRoute --> LangGraph1["Onboarding LangGraph<br/>• extract_signals_node (Verbatim quotes)<br/>• generate_response_node (MAX_FOLLOWUPS=2)"]
        LangGraph1 --> LLM1[Groq / Llama-3.3-70B]
        LangGraph1 --> FinalizeProfile["finalize_profile()<br/>Atomic self, wants, constraints"]
        FinalizeProfile --> ProfileDB[(PostgreSQL: profiles)]
    end

    subgraph MessagingPhase ["Phase 2: Event Distribution (RabbitMQ)"]
        FinalizeProfile -->|Enqueue| Q_Embed[Queue: belong.embedding]
    end

    subgraph EmbeddingPhase ["Phase 3: Vector Embeddings (belong-workers)"]
        Q_Embed --> EmbedWorker["EmbeddingWorker"]
        EmbedWorker --> Serializer["CanonicalSerializer<br/>(Deterministic Ordering)"]
        Serializer --> VoyageAPI["Voyage AI (voyage-3-lite)"]
        VoyageAPI --> Vectors["self_embedding & wants_embedding (512-dim)"]
        Vectors --> VectorDB[(PostgreSQL: pgvector profiles)]
        EmbedWorker -->|Enqueue| Q_Match[Queue: belong.matching]
    end

    subgraph MatchingPhase ["Phase 4: Two-Stage Matchmaking (belong-workers)"]
        Q_Match --> MatchWorker["MatchingWorker"]
        
        subgraph Stage1 ["Stage 1: pgvector Pre-Ranking"]
            MatchWorker --> Stage1SQL["Hard Filter SQL & Bidirectional Cosine Distance<br/>0.5*(1 - dist(A.wants, B.self)) + 0.5*(1 - dist(B.wants, A.self))"]
            Stage1SQL --> TopCandidates["Top Candidates (e.g. Top 15)"]
        end
        
        subgraph Stage2 ["Stage 2: Pairwise Reciprocal Reasoning"]
            TopCandidates --> PairwiseGraph["Pairwise LangGraph<br/>• format_prompt<br/>• llm_reasoning (Groq)<br/>• validation (ID -> Quote Resolution)"]
            PairwiseGraph --> ReciprocalResults["Evaluate reciprocal alignment:<br/>• complementary_alignments<br/>• shared_alignments<br/>• potential_conflicts<br/>• holistic_score"]
        end
        
        ReciprocalResults --> MatchDB[(PostgreSQL: compatibility_results)]
    end

    subgraph DeliveryPhase ["Phase 5: Match Discovery (belong-api)"]
        User -->|GET /api/matches| MatchRoute["Matches API Route"]
        MatchRoute --> MatchDB
        MatchRoute -->|JSON Payload| Response["Client Match Feed<br/>• Reciprocal & shared traits<br/>• Verbatim quotes<br/>• Verified compatibility"]
    end
```

### Explanation of Diagram
1. **Conversational Ingestion**: The user converses with the onboarding state machine. Signals with verbatim quotes are extracted and compiled into an atomic profile upon reaching the 2 follow-up hard cap.
2. **Deterministic Vectorization**: The profile is deterministically serialized and converted into dual 512-dimension vectors (`self` and `wants`) via Voyage AI.
3. **Stage 1 Fast Recall**: Candidate pairs are pre-filtered via hard constraints (gender, age, distance, goals) and pre-ranked via bidirectional cosine distance in pgvector.
4. **Stage 2 Deep Reasoning**: Groq's Llama-3.3-70B evaluates reciprocal dynamics ($A.\text{wants} \leftrightarrow B.\text{provides}$), separating complementary from shared alignments and resolving evidence IDs to user quotes.
5. **Client Presentation**: The client receives verified compatibility cards with transparent reasoning and verbatim evidence.

---

## 2. Microservice & Worker Responsibilities

```mermaid
flowchart LR
    subgraph BelongAPI ["belong-api (FastAPI)"]
        direction TB
        R1["/api/auth/*"]
        R2["/api/onboarding/*"]
        R3["/api/matches/*"]
        R4["/api/profile/*"]
    end

    subgraph WorkersEngine ["belong-workers (Python Background Daemon)"]
        direction TB
        W1["EmbeddingWorker"]
        W2["MatchingWorker"]
        W3["JobConsumer (RabbitMQ)"]
        W4["Pending Job Reconciler (PostgreSQL)"]
    end

    subgraph Infrastructure ["Shared Infrastructure"]
        direction TB
        PG[(PostgreSQL 16 + pgvector)]
        MQ([RabbitMQ Message Broker])
        Voyage[Voyage AI Vector API]
        Groq[Groq Llama 3.3 70B API]
    end

    BelongAPI <--> PG
    BelongAPI --> MQ
    WorkersEngine <--> PG
    WorkersEngine <--> MQ
    WorkersEngine --> Voyage
    WorkersEngine --> Groq
```

### Explanation of Diagram
- **`belong-api`**: Handles synchronous client HTTP requests, user sessions, chat progression, and serving compatibility results.
- **`belong-workers`**: Handles asynchronous background workloads (semantic serialization, vector generation, Stage 1 SQL retrieval, and Stage 2 LLM reasoning).
- **`Infrastructure`**: Durable storage (PostgreSQL with pgvector extension), reliable broker (RabbitMQ), and specialized AI APIs (Groq & Voyage AI).

---

## 3. Developer Summary & Key Boundaries

| Workflow Step | Executing Component | Key Invariant / SLA |
| :--- | :--- | :--- |
| **Onboarding Turn** | `belong-api` (LangGraph) | $\le 8$ user turns total; $\le 2$ follow-up limit |
| **Signal Extraction** | `extract_signals_node` | Verbatim quotes; confidence $\ge 0.50$ |
| **Vector Embedding** | `belong-workers` (EmbeddingWorker) | Dual 512-dim vectors; deterministic serialization |
| **Candidate Retrieval** | `belong-workers` (Stage 1 SQL) | Bidirectional cosine distance; HNSW index |
| **Reciprocal Reasoning** | `belong-workers` (Stage 2 LangGraph) | Separation of complementary vs shared alignments; no over-inference |
| **Match Discovery** | `belong-api` (`/api/matches`) | Fully resolved quotes and audit trail |
