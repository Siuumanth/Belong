# Developer Guide: Deterministic Canonical Semantic Embeddings (`belong-api`)

## 1. Executive Summary

This document explains the technical architecture, implementation, and operation of **Phase 5: Deterministic Semantic Serialization & Vector Embeddings** in `belong-api`.

In Belong, vector embeddings serve exclusively as a **Candidate Recall mechanism** (Stage 1 of Matchmaking) to retrieve top candidates efficiently using PostgreSQL `pgvector`. They are **not** the compatibility reasoning engine (Stage 2).

---

## 2. Updated System Architecture

```text
Frontend
   ↓
Go API Gateway
   ├── Auth Service
   └── Belong API
        ├── Onboarding / LangGraph
        ├── Profile CRUD
        ├── Protobuf / Canonical Serialization
        └── In-Process Embedding Worker
              ↓
        Embedding API (Hugging Face / Local)
              ↓
       PostgreSQL + pgvector

Belong API
     ↓
  RabbitMQ
     ↓
Matching Service (belong-workers)
 ├── Hard filters (SQL)
 ├── Vector candidate retrieval (pgvector)
 ├── Pairwise compatibility LLM reasoning
 └── Results
```

### Onboarding → Embedding Execution Flow

```text
6 questions completed
        ↓
LLM extracts signals
        ↓
finalize_profile()
        ↓
Save structured profile to DB
        ↓
Enqueue background task (FastAPI BackgroundTasks)
        ↓
Background Embedding Worker (in-process)
        ↓
Canonical Semantic Serialization
        ↓
Embedding API call
        ↓
self_embedding + wants_embedding
        ↓
Persist to PostgreSQL (pgvector)
```

### Key Architectural Decisions

* **No separate Embedding Microservice**: `belong-api` runs the embedding worker directly in-process via `BackgroundTasks`.
* **No RabbitMQ for Embeddings**: Embeddings are external I/O bound calls (API requests), not heavy local compute; in-process execution avoids unnecessary queue complexity.
* **RabbitMQ Reserved for Matching**: The Matching Service performs extensive vector retrieval and computationally expensive pairwise LLM evaluations, justifying independent scaling via RabbitMQ and `belong-workers`.
* **Asynchronous & Decoupled from Response**: Embeddings are computed in the background and not returned in the synchronous onboarding response; the worker updates PostgreSQL directly.

---

## 3. Canonical Semantic Serialization (`serializer.py`)

### Design Rationale
Freeform text generation by LLMs introduces non-deterministic noise (varying sentence structures, tone, and vocabulary across runs). `CanonicalSerializer` converts `StructuredProfileJSON` into standardized, section-based category text.

### Key Rules
1. **Direct Category Structure**: Group extracted signals under category headers (`Values`, `Lifestyle`, `Personality`, `Interests`, `Life goals`, `Conflict style`, `Provides`, `Emotional needs`, `Partner traits`, `Partner values`, `Relationship expectations`, `Desired lifestyle`).
2. **Confidence Filtering**: Only include evidence items where `confidence >= 0.5` (configured by `EMBEDDING_CONFIDENCE_THRESHOLD`).
3. **Omit Empty Categories**: If a section or category has no items meeting the confidence threshold, omit the category line completely to prevent dilution of the vector embedding.
4. **Strip Metadata & Quotes**: Keep evidence quotes, question IDs, and extraction metadata in `profile JSONB` for LLM compatibility reasoning, but exclude them from vector source text.

### Format Specs

**`SELF TEXT` Example:**
```text
SELF

Values: honesty, independence.
Lifestyle: enjoys travelling, active lifestyle.
Personality: supportive, social.
Interests: hiking, music.
Life goals: stable career, meaningful relationships.
Conflict style: prefers discussing problems openly.
Provides: emotional support, listens before giving advice.
```

**`WANTS TEXT` Example:**
```text
WANTS

Partner traits: emotionally available, independent.
Emotional needs: reassurance, emotional support.
Relationship expectations: open communication, mutual support.
Desired lifestyle: active, enjoys travelling.
Partner values: honesty, independence.
```

---

## 4. Embedding Generation Engine (`client.py`)

### Model Specifications
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Output Dimensions**: 384 dimensions (`VECTOR(384)`)

### Multi-Tiered Execution Strategy
`EmbeddingClient` is designed to be fully resilient across environments:

1. **Local Mode (Default when `sentence-transformers` is installed)**:
   - Uses PyTorch / `sentence-transformers` locally.
   - Runs model inference in an async executor thread for non-blocking execution.
2. **Hugging Face API Mode**:
   - Used when configured with `HF_API_TOKEN` or when local execution is disabled.
   - Calls HF Feature Extraction endpoint: `https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2`.
3. **Offline Mock Fallback**:
   - If no internet, no HF token, and no local `sentence-transformers` library are present, `EmbeddingClient` deterministically generates normalized 384-d pseudo-vectors using text hashing.
   - Ensures unit tests, local development, and CI environments never crash.

---

## 5. Database Schema & Persistence

Stored in the `profiles` table in PostgreSQL:

| Column | Type | Index | Description |
| :--- | :--- | :--- | :--- |
| `self_embedding` | `VECTOR(384)` | HNSW Cosine (`vector_cosine_ops`) | Vector representing what user offers/is |
| `wants_embedding` | `VECTOR(384)` | HNSW Cosine (`vector_cosine_ops`) | Vector representing what user desires |
| `embedding_source_text` | `JSONB` | N/A | Stores canonical text (`self_text`, `wants_text`, version, model) for debugging |

---

## 6. API Endpoints

### 1. Generate Profile Embeddings
`POST /api/profiles/{user_id}/embeddings`

**Response (`200 OK`):**
```json
{
  "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "self_text": "SELF\n\nValues: honesty, independence.\nLifestyle: active lifestyle.",
  "wants_text": "WANTS\n\nPartner traits: emotionally available.",
  "self_embedding_length": 384,
  "wants_embedding_length": 384,
  "status": "completed"
}
```

### 2. Fetch Embedding Status & Source Text
`GET /api/profiles/{user_id}/embeddings`

**Response (`200 OK`):**
```json
{
  "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "has_self_embedding": true,
  "has_wants_embedding": true,
  "embedding_source_text": {
    "self_text": "SELF\n\nValues: honesty.",
    "wants_text": "WANTS\n\nPartner traits: supportive.",
    "serializer_version": "v1_canonical",
    "model_name": "sentence-transformers/all-MiniLM-L6-v2"
  },
  "updated_at": "2026-09-16T15:25:00+00:00"
}
```

---

## 7. Testing & Verification

### Running Unit Tests
```bash
cd belong-api
python -m unittest discover -s tests -p "test_*.py"
```

### Direct Verification Script
```bash
python -c "
import asyncio
from uuid import uuid4
from embeddings.serializer import CanonicalSerializer
from embeddings.client import EmbeddingClient

async def run():
    client = EmbeddingClient()
    vec = await client.embed_text('SELF\n\nValues: honesty.')
    print(f'Generated vector of length {len(vec)}')

asyncio.run(run())
"
```
