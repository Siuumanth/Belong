# Belong

**An AI matchmaker that matches on compatibility, not similarity.**

## Use Case

Most dating/matchmaking apps optimize for surface-level similarity or swipe volume, which is a poor proxy for long-term relationship compatibility. Belong instead tries to match people whose **needs, emotional expectations, and behavior are compatible with each other** — even if they aren't similar people.

It's built as a technical learning project focused on **AI/RAG pipelines, LangGraph agents, embeddings, pgvector retrieval, and RabbitMQ async job processing**, rather than as a production dating product.

## What It Does

1. **Conversational onboarding** — Instead of a static form, an LLM-driven agent asks 6 broad, natural questions covering relationship intent, emotional needs, conflict style, lifestyle/values/interests, self-description, and dealbreakers. It asks up to 2 adaptive follow-ups only when an answer is vague or contradicts an earlier answer.

2. **Evidence-grounded profile extraction** — Every extracted trait is stored with a summary, a verbatim quote from the user's actual answer, and a confidence score. Nothing is invented; unknown stays unknown.

3. **Semantic + hard-constraint retrieval** — Profiles are represented using separate `self` and `wants` embeddings and searched through pgvector, after applying hard constraints such as age, location, relationship goal, and explicit dealbreakers.

4. **Pairwise compatibility reasoning** — For each shortlisted candidate, an LLM reasons over both people's **wants ↔ self** profiles in both directions and produces categorical verdicts — `strong alignment`, `partial`, `unclear`, or `conflict` — across relevant dimensions rather than a single fake compatibility score.

5. **Persisted, explainable results** — Every match comes with evidence supporting its identified alignments and conflicts.


## Architecture

```text
                        Frontend
                           │
                           ▼
                  ┌────────────────┐
                  │  Go Gateway    │
                  │ routing, auth, │
                  │ CORS, rate lim │
                  └───────┬────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
      Go Auth Service             belong-api
            │                    ├── Profile CRUD
         Auth DB                 ├── Onboarding (LangGraph)
                                 ├── Job creation
                                 └── Job/result reads
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

## Services

| Service | Language | Responsibility |
|---|---|---|
| `gateway` | Go | Routing, JWT auth, rate limiting, circuit breaker |
| `auth` | Go | User authentication, token issuance |
| `belong-api` | Python (FastAPI) | Profile CRUD, onboarding, job creation, result reads |
| `belong-workers` | Python | Embedding generation, matching pipeline (RabbitMQ consumers) |

## Design Principles

- **Vector similarity is for retrieval, not final compatibility.** Pairwise reasoning determines compatibility.

- **No fake-precision trait scores** such as `empathy: 8.7/10`.

- **Every non-null extracted claim must be grounded in a verbatim quote** from the user's answer.

- **Unknown stays unknown** rather than being filled in by the LLM.

- The system does **not claim to know exactly what someone needs**; it surfaces potential compatibility based on what they have expressed.

- The embedding representation uses **separate `self` and `wants` semantic representations**, enabling retrieval based on what one person wants and what another person offers.

- **Matching is fully async**: a match request creates a job → published to RabbitMQ → worker claims it → hard filtering → pgvector retrieval → pairwise LLM reasoning → results persisted → client polls for completion.