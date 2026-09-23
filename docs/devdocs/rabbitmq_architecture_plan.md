# Belong Architecture: RabbitMQ Migration Plan

> **Status**: Planned — to be implemented in Phase 6  
> **Decision date**: 2026-09-14  
> **Replaces**: Postgres-backed job queue (internal polling loop in python-belong)

---

## Why We're Moving to RabbitMQ

**Initial plan** was a Python modular monolith where a Postgres `jobs` table served as the job queue and a worker process within the same service polled for jobs with `SELECT ... FOR UPDATE SKIP LOCKED`.

**Updated plan** splits this into proper separate services driven by RabbitMQ. Reasons:
- Learning a real messaging pattern (not just a learning project shortcut)
- Separation of fast API workloads from expensive AI workloads
- Clean service boundary: `belong-api` publishes, `belong-workers` consumes
- Better scalability later (can scale workers independently)

---

## New Architecture

```
                         FRONTEND
                            │
                            ▼
                   ┌────────────────┐
                   │  Go Gateway    │
                   └───────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       Go Auth Service              belong-api
             │                     ├── Profile CRUD
          Auth DB                  ├── Onboarding (LangGraph)
                                   ├── Job creation
                                   └── Result reads
                                          │
                                          ▼
                                     RabbitMQ
                                    /         \
                                   ▼           ▼
                           Embedding       Matching
                            Worker          Worker
                              │               │
                              └───────┬───────┘
                                      ▼
                              PostgreSQL + pgvector
                                      │
                               ┌──────┴──────┐
                               ▼             ▼
                         LLM API       Hugging Face
                                       Embeddings
```

---

## Service Responsibilities

### belong-api (FastAPI)
Fast, user-facing. Handles:
- Profile CRUD
- Onboarding messages + LangGraph
- Creating embedding/matching jobs (publishes to RabbitMQ)
- Checking job status
- Reading match results

### belong-workers (Python async consumers)
Expensive AI workloads. Handles:
- **Embedding Worker**: profile JSON → semantic serializer → HuggingFace API → write VECTOR(384) to Postgres
- **Matching Worker**: hard SQL filters → pgvector retrieval → pairwise LLM compatibility reasoning → persist results → ranking

---

## RabbitMQ Design

### Exchange
- Name: `belong.jobs`
- Type: `direct`

### Queues
- `belong.embedding` — routing key: `embedding`
- `belong.matching` — routing key: `matching`

### Message Format
Messages are intentionally **small** — only enough to identify the job. Workers pull data from Postgres themselves.

```json
{
  "job_id": "abc123",
  "user_id": "user-uuid",
  "type": "embedding"
}
```

### Error Handling
- Success → ACK
- Recoverable error → NACK + requeue
- Permanent failure → Dead Letter Exchange

---

## Database Ownership Table

| Data                    | belong-api  | belong-workers |
|-------------------------|-------------|----------------|
| `profiles`              | Read/Write  | Read (embedding/matching workers write embeddings/results) |
| `conversations`         | Read/Write  | Read if needed |
| `jobs`                  | Create/Read | Claim/Update   |
| `self_embedding`, `wants_embedding` | Read | Write |
| `compatibility_results` | Read        | Write          |

Postgres remains the **single source of truth**. RabbitMQ only carries event signals.

---

## Implementation Order (Phase 6)

1. Uncomment RabbitMQ in `docker-compose.yml`
2. Implement `belong-workers/rabbitmq/connection.py` (aio-pika async connection)
3. Implement `belong-workers/rabbitmq/consumer.py` (message consumer + routing)
4. Implement `belong-workers/workers/embedding_worker.py` (full logic)
5. Add publisher to `belong-api` — publish embedding job when onboarding completes
6. Test full flow: onboarding complete → job published → worker picks up → embeddings written
7. Implement `belong-workers/workers/matching_worker.py` (Phase 7/8)

---

## What's Already Scaffolded

The `belong-workers/` folder exists with:
- `config.py` — all settings defined, RabbitMQ URLs ready
- `db/connection.py` — Postgres pool (same pattern as belong-api)
- `rabbitmq/connection.py` — stub with TODO comments
- `rabbitmq/consumer.py` — stub with TODO comments
- `workers/embedding_worker.py` — stub with documented flow
- `workers/matching_worker.py` — stub with documented flow
- `requirements.txt` — core deps active, aio-pika + LangGraph commented out for Phase 6
