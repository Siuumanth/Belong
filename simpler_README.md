# Belong — AI-Powered Compatibility Matching Engine

Modern dating apps are built largely around attraction, shared interests, and surface-level preferences. Belong takes a different approach by focusing on deeper relationship compatibility—understanding what people need, value, expect, and bring to a relationship, then using AI to identify meaningful connections beyond simple similarity.

---

## 🌟 How Belong Works (In Simple Terms)

Belong replaces superficial swiping with a **two-stage AI matching pipeline**:

```
 💬 Conversational Onboarding
           │
           ▼
 🧠 Trait Extraction Engine (Self vs. Wants)
           │
           ▼
 📐 Vector Embedding (OpenAI 1536d pgvector)
           │
           ▼
 ⚡ Stage 1: Fast Candidate Retrieval (SQL Hard Constraints + Bidirectional Vector Recall)
           │
           ▼
 🤖 Stage 2: Qualitative LLM Matching Agent (4 Dimensions + Signal ID Grounding)
```

### 1. Conversational Onboarding & Trait Extraction
Rather than filling out boring static forms, users participate in an empathetic, multi-turn AI interview. The system extracts structured signals about:
- **`self`**: Who the user is, their lifestyle, core values, conflict resolution style, and what they **provide** under stress.
- **`wants`**: What the user explicitly seeks in a long-term partner.

Every extracted signal is assigned a unique **`signal_id`** (e.g. `q2_emotional_needs_s_needs_00`) with exact quotes to prevent AI hallucinated claims.

### 2. Standardized Vector Embeddings
The system formats a user's extracted profile into standardized 3rd-person natural language text and converts them into **1536-dimensional vectors** using OpenAI (`text-embedding-3-small`):
- `self_embedding`: Vector representation of who the user is.
- `wants_embedding`: Vector representation of what the user desires.

### 3. Stage 1: Fast Candidate Retrieval Engine
Before running expensive AI reasoning on every candidate, **Stage 1** performs fast candidate recall directly in PostgreSQL:
1. **Hard SQL Filters**: Filters candidates by location distance (Haversine $\le 50\text{km}$), mutual gender preferences, and mutual age bounds.
2. **Bidirectional Vector Score**:
   - **Forward Similarity ($A.\text{wants} \rightarrow B.\text{self}$)**: Does candidate B match what user A wants?
   - **Reverse Similarity ($B.\text{wants} \rightarrow A.\text{self}$)**: Does user A match what candidate B wants?
   - $$\text{Combined Score} = 0.5 \times \text{Forward Sim} + 0.5 \times \text{Reverse Sim}$$

### 4. Stage 2: Qualitative LLM Reasoning Agent
The shortlisted candidates from Stage 1 are passed to a **LangGraph reasoning agent** (`belong-workers`). The agent evaluates 4 deep dimensions:
1. **Emotional Needs** (e.g. verbal reassurance vs. space)
2. **Core Values** (e.g. ambition, family, honesty)
3. **Lifestyle & Routine** (e.g. active morning routine vs. night owl)
4. **Conflict & Communication Style** (e.g. calm discussion vs. anxious pursuit vs. stonewalling)

It produces a detailed qualitative verdict (`strong_alignment`, `partial_alignment`, `conflict`) citing exact signal IDs for evidence.

---

## 🛠️ Low-Level Technical Architecture

Belong is built as a production-grade, asynchronous microservices platform:

```
[ Client / Web App ]
         │
         ▼
 ┌───────────────┐      ┌───────────────┐      ┌────────────────────────┐
 │  belong-api   │ ───> │   RabbitMQ    │ ───> │     belong-workers     │
 │ (FastAPI REST)│      │ (Message MQ)  │      │(Trait Extract & LLMs)  │
 └───────────────┘      └───────────────┘      └────────────────────────┘
         │                                                 │
         └──────────────────┐       ┌──────────────────────┘
                            ▼       ▼
                     ┌─────────────────────┐
                     │ PostgreSQL pgvector │
                     └─────────────────────┘
```

### Key Components
- **`belong-api`**: FastAPI HTTP REST API handling user profiles, onboarding sessions, and match triggering.
- **`belong-workers`**: Asynchronous Python worker processes handling trait extraction, OpenAI embedding creation, and LangGraph pairwise matching.
- **`PostgreSQL + pgvector`**: Stores user profiles, structured signals, spatial coordinates, and 1536d vector embeddings (`vector(1536)`).
- **`RabbitMQ`**: Non-blocking message broker for distributed task queues (`onboarding`, `embeddings`, `matching`).
- **`Docker Compose`**: Multi-container orchestration powering the complete environment.

---

## 📡 API Usage & Endpoint Reference

### 1. Start Conversational Onboarding Session
```http
POST /onboarding/session
Content-Type: application/json

{
  "user_id": "3a68a2c5-f3bd-40d7-8854-4b7d06413589"
}
```

### 2. Send Onboarding Interview Answer
```http
POST /onboarding/message
Content-Type: application/json

{
  "session_id": "9f214a1e-8422-491c-b6e1-d2e8b61c9401",
  "user_id": "3a68a2c5-f3bd-40d7-8854-4b7d06413589",
  "user_message": "I'm looking for a long-term partner in Bangalore who is emotionally available and communicates openly."
}
```

### 3. Fast Stage 1 Candidate Retrieval (Instant Vector Recall)
```http
GET /matches/retrieval/3a68a2c5-f3bd-40d7-8854-4b7d06413589
```
**Response Example:**
```json
{
  "user_id": "3a68a2c5-f3bd-40d7-8854-4b7d06413589",
  "total_candidates": 5,
  "candidates": [
    {
      "user_id": "c10e8d5c-9913-4039-85b1-0f928c110b0a",
      "name": "Bob",
      "age": 30,
      "gender": "male",
      "distance_km": 5.1,
      "cosine_similarity": 0.2208,
      "reverse_cosine_similarity": 0.2397,
      "combined_score": 0.2302
    }
  ]
}
```

### 4. Trigger Async Compatibility Matching Job
```http
POST /matches
X-User-ID: 3a68a2c5-f3bd-40d7-8854-4b7d06413589
```

### 5. Fetch Detailed Compatibility Results
```http
GET /matches/3a68a2c5-f3bd-40d7-8854-4b7d06413589
```

---

## 🚀 Running Locally

### 1. Start Services via Docker Compose
```bash
docker compose up -d --build
```

### 2. Run Ecosystem Benchmark Tests
```bash
# Evaluate Stage 1 Fast Vector Retrieval
python tests/evaluate_stage1_retrieval.py

# Run Full 10-User Ecosystem Test
python tests/run_10user_ecosystem.py
```
