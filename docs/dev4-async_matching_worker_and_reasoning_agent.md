# Async Matching Worker Engine & Pairwise Compatibility Reasoning Agent

This document details **Phase 6 & Phase 8** architecture: the asynchronous background worker engine ([`belong-workers`](file:///d:/code/Golang/Belong/belong-workers)), RabbitMQ message queuing, the **LangGraph Pairwise Compatibility Reasoning Agent (Groq LLM)**, deterministic candidate ranking, and match status polling APIs.

---

## 1. System Architecture & Service Boundaries

```text
[ Client / Auth Gateway ]
        │
        ▼ (HTTP POST /api/matches with X-User-ID)
┌────────────────────────────────────────────────────────┐
│                      belong-api                        │
│ 1. Inserts job record into PostgreSQL (status=pending) │
│ 2. Publishes job event to RabbitMQ (belong.matching)   │
│ 3. Returns HTTP 202 Accepted + job_id                  │
│ 4. Serves GET /api/matches/jobs/{job_id} (Status Poll) │
│ 5. Serves GET /api/matches/{user_id} (Fetch Matches)   │
└──────────────────────────┬─────────────────────────────┘
                           │ RabbitMQ Exchange (belong.jobs)
                           ▼
┌────────────────────────────────────────────────────────┐
│                     belong-workers                     │
│ 1. Consumes job message from queue                     │
│ 2. Updates DB job status → "running"                   │
│ 3. Stage 1: SQL hard filters + pgvector top N recall   │
│ 4. Stage 2: LangGraph Pairwise LLM Agent (Groq)        │
│ 5. Deterministic multi-dimensional candidate ranking   │
│ 6. Persists records to compatibility_results table     │
│ 7. Updates DB job status → "completed"                 │
└──────────────────────────┬─────────────────────────────┘
                           │ (Fallback if RabbitMQ missed)
                           ▼
             PostgreSQL Pending Job Reconciler 
           (FOR UPDATE SKIP LOCKED background loop)
```

---

## 2. Service Responsibilities

### `belong-api` (Lightweight API Dispatcher)
- **Role**: Non-blocking HTTP endpoint handler.
- **Security**: Derives `user_id` strictly from authenticated request headers (`X-User-ID`).
- **Dispatch**: Writes job record to `jobs` table (`type='matching'`, `status='pending'`) and publishes to RabbitMQ via `aio-pika`.
- **Fallback**: If RabbitMQ is offline, `belong-api` leaves the job as `pending` in PostgreSQL without running expensive AI code directly inside the Web API process.

### `belong-workers` (Asynchronous Heavy AI Worker Engine)
- **Role**: Background worker engine executing compute-intensive AI operations.
- **Consumer**: Listens on RabbitMQ queues (`belong.matching`, `belong.embedding`) via `aio-pika`.
- **Reconciler**: Runs a periodic PostgreSQL background loop claiming unacknowledged `pending` jobs using `SELECT ... FOR UPDATE SKIP LOCKED` for 100% execution guarantees.

---

## 3. Stage 2: LangGraph Pairwise Compatibility Reasoning Agent

Located in [`belong-workers/matching/compatibility.py`](file:///d:/code/Golang/Belong/belong-workers/matching/compatibility.py), the pairwise reasoning agent evaluates relational fit between candidate profiles using **Groq LLM** (`llama-3.3-70b-versatile`).

### 3.1 Evaluation Rules & Constraints

1. **Qualitative Verdicts Only**: Avoids artificial numerical scores (e.g. `87/100`) to prevent false precision. Uses 4 categorical verdicts:
   - `"strong_alignment"`
   - `"partial_alignment"`
   - `"unclear"`
   - `"conflict"`
2. **Bidirectional Comparison**: Evaluates `User A wants → User B provides` AND `User B wants → User A provides`.
3. **Anti-Hallucination Evidence Extraction**: Requires verbatim evidence quotes from User A (`evidence_a`) and User B (`evidence_b`) for every dimension.
4. **4 Core Compatibility Dimensions**:
   - `emotional_needs`: Stress response, emotional support, vulnerability.
   - `core_values`: Life principles, ethics, relationship intent, dealbreakers.
   - `lifestyle`: Daily habits, hobbies, energy levels, future life building.
   - `conflict_style`: Disagreement resolution and communication tendencies.

### 3.2 LangGraph State Machine Architecture

```text
    ┌──────────────────────┐
    │ format_prompt_node   │
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │ llm_reasoning_node   │ (Groq LLM + Pydantic Structured Output)
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │   validation_node    │ (Verifies verdicts & quote completeness)
    └──────────┬───────────┘
               ▼
             [END]
```

### 3.3 Output Schema (`PairwiseCompatibilityOutput`)

```json
{
  "overall_verdict": "strong_alignment",
  "dimension_results": {
    "emotional_needs": {
      "verdict": "strong_alignment",
      "evidence_a": "Needs partner who remains calm and reassuring during stress.",
      "evidence_b": "Naturally calm under pressure and provides steady support."
    },
    "core_values": {
      "verdict": "strong_alignment",
      "evidence_a": "Values honesty and long-term commitment.",
      "evidence_b": "Building a stable family foundation is top priority."
    },
    "lifestyle": {
      "verdict": "partial_alignment",
      "evidence_a": "Enjoys active weekend hiking and outdoor travel.",
      "evidence_b": "Prefers quiet weekend reading and home cooking."
    },
    "conflict_style": {
      "verdict": "strong_alignment",
      "evidence_a": "Prefers open, direct conversation after taking 10 minutes to process.",
      "evidence_b": "Values thoughtful discussion rather than shouting."
    }
  },
  "strong_alignments": ["Shared commitment goals", "Emotional support style compatibility"],
  "potential_conflicts": ["Slight pace difference in weekend outdoor activity preferences"],
  "dealbreaker_violations": [],
  "uncertainties": []
}
```

---

## 4. Deterministic Multi-Dimensional Candidate Ranking

Located in [`belong-workers/matching/ranking.py`](file:///d:/code/Golang/Belong/belong-workers/matching/ranking.py), candidates are ranked using a multi-field deterministic sort key tuple:

```python
def calculate_rank_key(output: PairwiseCompatibilityOutput, stage1_combined_score: float) -> tuple:
    return (
        -len(output.dealbreaker_violations),  # 1. Zero dealbreaker violations prioritized (0 > -1)
        VERDICT_RANK.get(output.overall_verdict, 1), # 2. strong_alignment(4) > partial(3) > unclear(2) > conflict(1)
        len(output.strong_alignments) - len(output.potential_conflicts), # 3. Net alignment balance
        stage1_combined_score # 4. Stage 1 pgvector bidirectional score tie-breaker
    )
```

---

## 5. Database Schemas

### `jobs` Table
Tracks asynchronous job state lifecycle (`pending` → `running` → `completed` / `failed`):

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type TEXT NOT NULL,                     -- 'matching' or 'embedding'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NULL,
    attempts INT NOT NULL DEFAULT 0,
    error TEXT NULL,
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### `compatibility_results` Table
Persists qualitative evaluation breakdowns and quote evidence per user pair:

```sql
CREATE TABLE IF NOT EXISTS compatibility_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a_id UUID NOT NULL,
    user_b_id UUID NOT NULL,
    dimension_results JSONB NOT NULL DEFAULT '{}'::jsonb,
    strong_alignments JSONB NOT NULL DEFAULT '[]'::jsonb,
    potential_conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
    dealbreaker_violations JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainties JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_name TEXT,
    reasoning_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_compatibility_pair_version UNIQUE (user_a_id, user_b_id, reasoning_version)
);
```

---

## 6. API Endpoint Specifications

### 6.1 `POST /api/matches`
- **Description**: Enqueues an asynchronous compatibility matching job for the authenticated user.
- **Auth**: Requires `X-User-ID` header.
- **Response** (`HTTP 202 Accepted`):
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "type": "matching",
  "status": "pending",
  "created_at": "2026-09-17T20:00:00Z"
}
```

### 6.2 `GET /api/matches/jobs/{job_id}`
- **Description**: Polls status and execution progress of a matching job.
- **Response** (`HTTP 200 OK`):
```json
{
  "job_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "type": "matching",
  "status": "completed",
  "attempts": 1,
  "error": null,
  "started_at": "2026-09-17T20:00:01Z",
  "completed_at": "2026-09-17T20:00:08Z",
  "result": {
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "total_matches": 5,
    "matches_persisted": 5
  }
}
```

### 6.3 `GET /api/matches/{user_id}`
- **Description**: Retrieves ranked compatibility match recommendations for `user_id`.
- **Response** (`HTTP 200 OK`):
```json
{
  "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "total_matches": 1,
  "matches": [
    {
      "user_b_id": "c1fec238-1234-4ef8-9900-8bb9bd380b22",
      "overall_verdict": "strong_alignment",
      "dimension_results": { ... },
      "strong_alignments": ["Shared commitment goals"],
      "potential_conflicts": [],
      "dealbreaker_violations": [],
      "uncertainties": []
    }
  ]
}
```
