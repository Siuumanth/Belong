# belong-workers

Worker service for Belong — consumes jobs from RabbitMQ and handles expensive AI workloads (embeddings, matching, compatibility reasoning).

## Responsibilities

- **Embedding Worker**: reads profile JSON from Postgres → serializes → calls Hugging Face API → writes VECTOR(384) embeddings back to Postgres
- **Matching Worker**: hard constraint filtering → pgvector retrieval → pairwise LLM compatibility reasoning → persist results

## NOT implemented yet

RabbitMQ integration and worker logic will be added in Phase 5 (Embeddings) and Phase 6 (Job Worker Engine).

## Structure

```
belong-workers/
├── main.py              # Worker entrypoint (stub)
├── config.py            # Configuration
├── requirements.txt     # Dependencies
├── .env.example
├── db/
│   ├── __init__.py
│   └── connection.py    # Postgres connection pool
├── rabbitmq/
│   ├── __init__.py
│   ├── connection.py    # aio-pika RabbitMQ manager (TODO)
│   └── consumer.py      # Message consumer + dispatcher (TODO)
└── workers/
    ├── __init__.py
    ├── embedding_worker.py   # Embedding job handler (TODO)
    └── matching_worker.py    # Matching job handler (TODO)
```
