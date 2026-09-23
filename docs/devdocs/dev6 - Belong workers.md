# Belong Workers — Developer Documentation

> A deep-dive into how the `belong-workers` background job engine works, from boot to job completion.

---

## Overview

`belong-workers` is a standalone Python async service that runs **two types of background jobs**:

| Job Type | What it does |
|---|---|
| `embedding` | Turns a user's profile into semantic vectors and stores them |
| `matching` | Finds and ranks compatible partners for a user using those vectors + an LLM |

Jobs arrive via **two complementary channels** — RabbitMQ (primary) and a PostgreSQL polling loop (fallback). Both ultimately call the same worker classes.

---

## High-Level Architecture

```
                    ┌──────────────────────────────────────────┐
                    │           belong-workers (main.py)        │
                    │                                          │
      RabbitMQ ────►│  JobConsumer          reconcile_pending_jobs() │
                    │  (real-time)          (every 15s fallback)     │
                    │       │                       │           │
                    └───────┼───────────────────────┼───────────┘
                            │                       │
                     ┌──────▼──────┐         ┌──────▼──────┐
                     │ EmbeddingWorker │       │ MatchingWorker │
                     └──────┬──────┘         └──────┬──────┘
                            │                       │
                    PostgreSQL (profiles, jobs, compatibility_results)
```

---

## Startup Sequence (`main.py`)

When you run `python main.py`, here's what happens in order:

1. **Logger is initialized** — structured `[INFO]` logs to stdout.
2. **DB connection pool is opened** — `init_pool()` creates a psycopg async pool (min 2, max 10 connections) pointed at `POSTGRES_HOST`.
3. **RabbitMQ connection is attempted** — if RabbitMQ is reachable, `JobConsumer.start_listening()` binds to the `belong.matching` and `belong.embedding` queues. If it fails, a warning is logged but the process continues.
4. **DB reconciler loop is launched** — `reconcile_pending_jobs()` runs as a background asyncio task, checking the `jobs` table every **15 seconds** for any jobs that were missed.
5. **Signal handlers are registered** — `SIGINT` / `SIGTERM` trigger a clean shutdown (cancel reconciler, close RabbitMQ, drain DB pool).

---

## Job Delivery: Two Paths

### Path 1 — RabbitMQ (Primary)

```
Producer (belong-api) ──► RabbitMQ Exchange: belong.jobs
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
           Queue: belong.matching      Queue: belong.embedding
                    │                           │
             JobConsumer.process_message()
```

- Exchange type: **Direct** (durable)
- Routing keys: `matching` → `belong.matching` queue, `embedding` → `belong.embedding` queue
- Prefetch count: **5** (limits concurrent in-flight messages per consumer)
- Message body is JSON: `{ "job_id": "...", "type": "matching"|"embedding", "user_id": "..." }`

**When a message arrives**, `process_message()` does:
1. Parses the JSON body.
2. Updates the `jobs` row to `status = 'running'` in Postgres (atomically increments `attempts`).
3. Calls the appropriate worker's `execute()` method.
4. On success → sets `status = 'completed'` and stores the result JSON.
5. On failure → sets `status = 'failed'` and stores the error string.

> The message is **ACK'd after processing** (via `message.process(requeue=False)`). Failed jobs are not requeued to RabbitMQ — they stay as `failed` in the DB.

---

### Path 2 — DB Reconciler (Fallback)

Runs every 15 seconds regardless of RabbitMQ health. Queries the `jobs` table for any row where:
- `status = 'pending'`
- `available_at <= NOW()`
- `attempts < 3`

Uses `SELECT ... FOR UPDATE SKIP LOCKED` — a safe concurrency pattern that prevents multiple worker instances from picking the same job.

If a job is found, it's claimed (`status = 'running'`) and executed the same way as the RabbitMQ path.

---

## The Workers

### EmbeddingWorker (`workers/embedding_worker.py`)

**Triggered when:** A user's profile is created or updated and needs to be vectorized.

**Steps:**

```
1. Fetch profile JSON from `profiles` table (by user_id)
        ↓
2. CanonicalSerializer → splits profile into two text strings:
     - self_text  : "who this person is"
     - wants_text : "who this person is looking for"
        ↓
3. EmbeddingClient → calls HuggingFace API (or local model)
     - Generates self_embedding  (384-dim vector)
     - Generates wants_embedding (384-dim vector)
        ↓
4. UPDATE profiles SET self_embedding = ..., wants_embedding = ...
```

**Output stored in DB:**
```json
{ "user_id": "...", "self_embedding_generated": true, "wants_embedding_generated": true }
```

> The `CanonicalSerializer` and `EmbeddingClient` are shared from the `belong-api` package (loaded via sys.path injection).

---

### MatchingWorker (`workers/matching_worker.py`)

**Triggered when:** A user requests to see their matches. This is the core intelligence of the system — a two-stage pipeline.

**Full flow:**

```
1. Fetch User A's profile from Postgres
        ↓
2. STAGE 1 — CandidateRetriever (pgvector recall)
        ↓
3. STAGE 2 — PairwiseCompatibilityAgent (LLM reasoning per candidate)
        ↓
4. rank_candidates() — deterministic scoring
        ↓
5. UPSERT into compatibility_results table
```

---

#### Stage 1: Candidate Retrieval (`matching/retrieval.py`)

The goal here is to quickly **narrow the entire user base** down to a manageable shortlist using database-level filters and vector math.

**Hard filters applied (SQL WHERE clauses):**
| Filter | Logic |
|---|---|
| **Gender / Preferences** | User A's gender must be in candidate's preferred_genders, and vice versa |
| **Age range** | Both users must fall within each other's preferred_age_min / max |
| **Relationship goal** | Must match if `required_relationship_goal` is set |
| **Geographic distance** | Haversine formula applied in SQL; filtered by `max_distance_km` |

**Vector recall:**
After filters, candidates are sorted by `cosine_distance` between **User A's `wants_embedding`** and **Candidate's `self_embedding`**. The top `candidate_pool_limit` (default: 50) are returned.

**Bidirectional scoring (post-processing):**
For each candidate, a `combined_score` is calculated:
```
combined_score = (1 - weight) × forward_similarity + weight × reverse_similarity
```
- **Forward:** "Does candidate's self match what User A wants?"
- **Reverse:** "Does User A's self match what candidate wants?"
- Default weight: `0.5` (equal bidirectional)

The pool is then trimmed to the top `pre_rank_limit` (default: 15) by combined score. These are the candidates that proceed to Stage 2.

---

#### Stage 2: LLM Pairwise Reasoning (`matching/compatibility.py`)

For each shortlisted candidate, a **LangGraph graph** is invoked to produce a structured compatibility report.

**LangGraph pipeline (3 nodes):**

```
format_prompt_node
      ↓
llm_reasoning_node  (calls Groq LLM with structured output)
      ↓
validation_node     (normalizes unexpected verdicts)
      ↓
    END
```

**Node 1 — `format_prompt_node`:**
Injects User A and User B profile JSONs into the configurable `PAIRWISE_REASONING_PROMPT_TEMPLATE`.

**Node 2 — `llm_reasoning_node`:**
Calls the configured LLM (default: Groq `llama-3.3-70b-versatile`) with structured output enforced via `llm.with_structured_output(PairwiseCompatibilityOutput)`.

The LLM is asked to evaluate **4 core dimensions**, producing evidence quotes from each profile:

| Dimension | What's evaluated |
|---|---|
| `emotional_needs` | Stress response, vulnerability, support styles |
| `core_values` | Ethics, dealbreakers, relationship intent |
| `lifestyle` | Habits, hobbies, energy, future plans |
| `conflict_style` | How disagreements are handled |

Each dimension gets a verdict: `strong_alignment` / `partial_alignment` / `unclear` / `conflict`.

**Node 3 — `validation_node`:**
Ensures the `overall_verdict` is one of the four valid values. Defaults unrecognized verdicts to `"unclear"`.

---

#### Ranking (`matching/ranking.py`)

After all candidates are evaluated by the LLM, they are **deterministically sorted** using a 4-tuple sort key (descending priority):

```
1. Fewest dealbreaker violations  (0 is best — penalty is -len(violations))
2. Verdict score                  (strong_alignment=4, partial=3, unclear=2, conflict=1)
3. Net alignment                  (strong_alignments count - potential_conflicts count)
4. Stage 1 combined_score         (vector similarity tie-breaker)
```

---

#### Persisting Results

Results are upserted into `compatibility_results` using `ON CONFLICT (user_a_id, user_b_id, reasoning_version) DO UPDATE`. This means re-running a matching job for the same user simply refreshes the existing results rather than creating duplicates.

Stored fields per pair:
- `dimension_results` — per-dimension verdicts and evidence (JSONB)
- `strong_alignments` — list of alignment highlights (JSONB)
- `potential_conflicts` — list of friction areas (JSONB)
- `dealbreaker_violations` — hard no-gos triggered (JSONB)
- `uncertainties` — areas with insufficient info (JSONB)
- `reasoning_version` — currently hardcoded to `'v1'`

---

## Key Data Models

### `CandidateMatch` (Stage 1 output)
```python
user_id, age, gender, orientation, relationship_goal
latitude, longitude, distance_km
cosine_similarity, reverse_cosine_similarity, combined_score
profile: Dict  # raw profile JSON
```

### `PairwiseCompatibilityOutput` (Stage 2 output)
```python
overall_verdict: str          # "strong_alignment" | "partial_alignment" | "unclear" | "conflict"
dimension_results: DimensionResults  # 4 dimensions each with verdict + evidence_a + evidence_b
strong_alignments: List[str]
potential_conflicts: List[str]
dealbreaker_violations: List[str]
uncertainties: List[str]
```

---

## Configuration (`config.py`)

All settings come from environment variables with sensible defaults.

| Key | Default | Purpose |
|---|---|---|
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection |
| `RABBITMQ_EXCHANGE` | `belong.jobs` | Exchange name |
| `RABBITMQ_QUEUE_MATCHING` | `belong.matching` | Matching queue |
| `RABBITMQ_QUEUE_EMBEDDING` | `belong.embedding` | Embedding queue |
| `LLM_PROVIDER` | `groq` | `groq` / `google` / `openai` |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model name |
| `LLM_TEMPERATURE` | `0.2` | Low temp for consistent reasoning |
| `GROQ_API_KEY` | _(required for Groq)_ | API key |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `384` | Vector dimensionality |
| `USE_LOCAL_EMBEDDINGS` | `true` | Use local model vs HF API |
| `EMBEDDING_CONFIDENCE_THRESHOLD` | `0.5` | Min similarity to consider |

---

## Database Tables Used

| Table | Used by | Purpose |
|---|---|---|
| `jobs` | Both workers + reconciler | Job status lifecycle tracking |
| `profiles` | Both workers | Source of user data and embeddings |
| `compatibility_results` | MatchingWorker | Stores final pairwise reasoning output |

---

## Error Handling Summary

| Scenario                                | Behavior                                                |
| --------------------------------------- | ------------------------------------------------------- |
| RabbitMQ unavailable on startup         | Warning logged, reconciler loop takes over              |
| Missing `user_id` in payload            | `ValueError` raised, job marked `failed`                |
| User profile not in DB                  | `ValueError` raised, job marked `failed`                |
| User has no `wants_embedding`           | Returns early with 0 matches                            |
| LLM call fails for a candidate pair     | Error logged, that candidate is skipped; others proceed |
| LangGraph produces unrecognized verdict | Normalized to `"unclear"`                               |
| Job exceeds 3 attempts                  | Reconciler stops picking it up                          |

---

## Module Map

```
belong-workers/
├── main.py                      # Entrypoint: boots pool, consumer, reconciler
├── config.py                    # WorkerSettings — all env-driven config
├── db/
│   └── connection.py            # Async psycopg connection pool
├── rabbitmq/
│   ├── connection.py            # RabbitMQManager — robust aio-pika connection
│   └── consumer.py              # JobConsumer — dispatches to workers, updates DB
├── workers/
│   ├── embedding_worker.py      # EmbeddingWorker.execute()
│   └── matching_worker.py       # MatchingWorker.execute()
└── matching/
    ├── retrieval.py             # CandidateRetriever — Stage 1 pgvector recall
    ├── compatibility.py         # PairwiseCompatibilityAgent — LangGraph LLM graph
    ├── ranking.py               # rank_candidates() — deterministic sort
    └── schemas.py               # Pydantic models: CandidateMatch, PairwiseCompatibilityOutput
```
