# belong-workers

Worker service for Belong — consumes jobs from RabbitMQ and handles expensive background AI workloads (embeddings, pgvector candidate retrieval, pairwise LLM compatibility reasoning).

## Core Dependencies

- **`psycopg` & `psycopg_pool`**: Async PostgreSQL 16 + pgvector database connection pool.
- **`pydantic`**: Pydantic v2 data validation and structured compatibility output schemas.
- **`aio-pika`**: Persistent RabbitMQ AMQP connection manager, channel lifecycle, and queue message consumers (`belong.matching`, `belong.embedding`).
- **`langgraph` & `langchain-groq`**: LangGraph Pairwise Compatibility Reasoning Agent powered by Groq LLM (`llama-3.3-70b-versatile`).

## Responsibilities & Worker Tasks

- **Matching Worker** (`workers/matching_worker.py`):
  1. Stage 1 Retrieval: Hard SQL constraint filters (gender, age, distance, relationship goals) + pgvector bidirectional cosine distance recall.
  2. Stage 2 Pairwise LLM Agent: Evaluates shortlisted candidates via Groq LangGraph agent across 4 dimensions (`emotional_needs`, `core_values`, `lifestyle`, `conflict_style`) producing qualitative verdicts and exact evidence quotes.
  3. Deterministic Ranking: Ranks candidates by dealbreaker count, verdict hierarchy, and net alignment score.
  4. Database Persistence: Writes structured records to `compatibility_results` and marks job `completed`.

- **Embedding Worker** (`workers/embedding_worker.py`):
  1. Reads profile JSON from PostgreSQL `profiles` table.
  2. Runs canonical semantic serializer (`CanonicalSerializer`).
  3. Generates 384-dim vector embeddings for `self_embedding` and `wants_embedding`.
  4. Updates `profiles` table in PostgreSQL and marks job `completed`.

- **PostgreSQL Pending Job Reconciler**:
  - Background loop in `main.py` that periodically queries PostgreSQL for unacknowledged `pending` jobs (`FOR UPDATE SKIP LOCKED`) if RabbitMQ delivery was missed or offline.

## Project Structure

```
belong-workers/
├── main.py                   # Worker entrypoint & DB fallback reconciler loop
├── config.py                 # Worker settings (PostgreSQL, RabbitMQ, Groq LLM, Prompt templates)
├── requirements.txt          # Dependencies (psycopg, pydantic, aio-pika, langgraph, etc.)
├── .env.example
├── db/
│   └── connection.py         # Async psycopg_pool database connection manager
├── rabbitmq/
│   ├── connection.py         # Persistent aio-pika RabbitMQ connection & queue setup
│   └── consumer.py           # Message consumer, job dispatcher & status state manager
├── matching/
│   ├── schemas.py            # Pydantic schemas (DimensionResults, PairwiseCompatibilityOutput, CandidateMatch)
│   ├── retrieval.py          # Stage 1 SQL hard filters & pgvector retrieval engine
│   ├── compatibility.py      # Stage 2 LangGraph Pairwise Compatibility Reasoning Agent (Groq)
│   └── ranking.py            # Deterministic multi-dimensional candidate ranking algorithm
└── workers/
    ├── embedding_worker.py   # Embedding worker task handler
    └── matching_worker.py    # Matching worker task handler
```

## Running Locally

```bash
# 1. Create virtual environment & install dependencies
uv venv
uv pip install -r requirements.txt

# 2. Run worker service
python main.py
```
