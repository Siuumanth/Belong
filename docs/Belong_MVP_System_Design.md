**Belong — MVP System Design**

_AI-assisted compatibility matching platform | Go Gateway + Python modular service + PostgreSQL/pgvector_

Belong is an AI-powered matchmaking platform focused on compatibility, not just similarity.

Most dating platforms primarily help you discover people based on attraction, shared interests, preferences, or basic filters. But being interested in someone and actually being compatible with them are two different things.

Belong takes a different approach. During onboarding, an AI agent has a meaningful conversation with you to understand what you want from a relationship, what you need from a partner, what you naturally offer, your values, lifestyle, conflict style, and deal-breakers. It turns those conversations into a structured understanding of the person rather than relying only on predefined profile fields.

When finding matches, Belong first filters candidates using hard constraints and then uses semantic retrieval to find people whose profiles are relevant. But instead of stopping at similarity, it performs pairwise compatibility reasoning in both directions:

What does A need, and does B provide it?
What does B need, and does A provide it?

It then evaluates areas such as emotional needs, values, lifestyle, conflict styles, and deal-breakers, while showing the reasoning and evidence behind the compatibility.

So the goal isn't to say “you both like hiking, therefore you're a good match.” It's to answer a much more meaningful question:

“Given what these two people actually want and offer in a relationship, where do they genuinely align, and where might they struggle?”

That's what makes Belong different: it moves matchmaking from finding people who look similar on paper to understanding whether two people can actually complement each other.

# 1\. MVP Scope

Belong is a compatibility-oriented matchmaking system. The MVP focuses on turning conversational onboarding answers into a structured profile, retrieving plausible candidates, and using pairwise LLM reasoning to explain compatibility. It is deliberately not a full dating product.

- In scope: onboarding, profile management, embeddings, hard filtering, vector retrieval, pairwise compatibility reasoning, ranking, and persisted results.
- Out of scope: real-time messaging, payments, notifications, production recommendation feedback loops, mobile apps, and complex distributed infrastructure.
- Authentication remains in the existing Go Auth service.
- The frontend communicates only with the Go API Gateway; it does not directly call internal Python components.

# 2\. High-Level Architecture

```
                         Web / CLI Client
                                |
                                v
                       +------------------+
                       |  Go API Gateway  |
                       | routing, auth,   |
                       | CORS, rate limit |
                       +--------+---------+
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
     +---------------+                    +-----------------------+
     | Go Auth       |                    | Python Belong Service |
     | Service       |                    |                       |
     +-------+-------+                    |  FastAPI API Process  |
             |                            |  Worker Process(es)   |
             v                            |  Profile / Matching   |
         Auth DB                          |  Onboarding / Agents  |
                                          +----------+------------+
                                                     |
                              +----------------------+----------------+
                              |                                       |
                              v                                       v
                    +--------------------+                    +---------------+
                    | PostgreSQL         |                    | External APIs |
                    | + pgvector         |                    | LLM API       |
                    | profiles, jobs,    |                    | Hugging Face  |
                    | conversations,     |                    | embeddings    |
                    | compatibility      |                    +---------------+
                    +--------------------+
```

# 3\. Python Service Runtime Model

The Python side is one codebase and one logical service, but the API and long-running workloads run as separate processes. This avoids making CRUD requests compete with expensive LLM workflows while keeping the MVP simple.

```
python-belong/
├── api/                    # FastAPI routes + request/response models
├── profile/                # profile CRUD and validation
├── onboarding/             # LangGraph onboarding workflow
├── embeddings/             # semantic text + Hugging Face embedding client
├── matching/
│   ├── retrieval.py        # hard filters + pgvector
│   ├── compatibility.py   # compatibility agent interface
│   └── ranking.py          # result ranking
├── jobs/                   # job creation, claiming, status updates
├── db/                     # pool + queries/repositories
└── main.py

Runtime:
├── belong-api              # FastAPI; handles short requests
└── belong-worker           # polls/claims jobs; runs long workflows
```

# 4\. Why Separate API and Worker Processes?

CRUD operations are short-lived database requests, while matching can involve retrieval plus many LLM calls. Putting both in one runtime process creates unnecessary contention and makes long requests harder to manage. Two processes preserve the modular-monolith design while allowing API and worker capacity to be scaled separately.

| **Workload**         | **Process**   | **Typical behavior**                                   |
| -------------------- | ------------- | ------------------------------------------------------ |
| Profile CRUD         | API           | Fast DB request/response                               |
| Read match results   | API           | Fast DB read                                           |
| Onboarding message   | API initially | LLM call(s), short conversational request              |
| Embedding generation | Worker        | External embedding API call; persisted result          |
| Full matching        | Worker        | Retrieval + multiple compatibility LLM calls + ranking |

# 5\. Job Model

For the MVP, jobs can be implemented using PostgreSQL itself rather than Kafka/RabbitMQ. A matching request creates a durable row in a jobs table. Workers poll for pending jobs, atomically claim one, execute it, and persist the result.

```
Client
  |
  | POST /matches
  v
FastAPI
  |
  | INSERT job(status='pending')
  v
PostgreSQL
  |
  | returns job_id immediately
  v
Client: 202 Accepted
  |
  | GET /matches/jobs/{job_id}
  v
FastAPI
  |
  v
PostgreSQL ---> status / result

Meanwhile:
Worker
  |
  | claim pending job
  v
PostgreSQL
  |
  +--> hard filters
  +--> pgvector retrieval
  +--> compatibility LLM calls
  +--> rank
  +--> save compatibility_results
  +--> mark job completed
```

# 6\. Job Lifecycle

| **State** | **Meaning**                                      |
| --------- | ------------------------------------------------ |
| pending   | Job created but not claimed.                     |
| running   | A worker has claimed and is executing it.        |
| completed | Results are persisted and available.             |
| failed    | Execution failed after the allowed retry policy. |
| cancelled | Optional MVP state; can be omitted initially.    |

1. API inserts a job with a UUID, type, payload, and status=pending.
2. Worker finds a pending job and atomically changes it to running. Use row locking / SKIP LOCKED so two workers do not claim the same job.
3. Worker executes the workflow.
4. Successful output is written to compatibility_results; job becomes completed.
5. On failure, record error information and either retry or mark failed.
6. The client polls the job endpoint and retrieves results when completed.

# 7\. Main Matching Flow

```
POST /matches
     |
     v
Create matching_job
     |
     v
Worker claims job
     |
     +--> 1. Load requesting profile
     |
     +--> 2. Hard constraint filtering
     |       age / distance / gender / goal / dealbreakers
     |
     +--> 3. pgvector retrieval
     |       A.wants_embedding -> candidates.self_embedding
     |       shortlist ~50-100
     |
     +--> 4. Optional cheap reduction
     |       shortlist ~10-20
     |
     +--> 5. Compatibility agent
     |       A wants -> B self
     |       B wants -> A self
     |       values / lifestyle / emotional needs / conflict style
     |
     +--> 6. Persist pairwise results
     |
     +--> 7. Rank candidates
     |
     +--> 8. Mark job completed
             |
             v
       GET /matches/jobs/{id}
```

# 8\. Onboarding Flow

```
POST /onboarding/session
        |
        v
Create conversation
        |
        v
POST /onboarding/message
        |
        v
LangGraph state
  ├── determine next core question
  ├── collect answer
  ├── extract signals + evidence + confidence
  ├── detect contradictions
  ├── check must-have fields
  └── ask <= 2 adaptive follow-ups when needed
        |
        v
Profile saved
        |
        v
Create embedding job(s)
        |
        v
Worker -> Hugging Face embedding API
        |
        v
self_embedding / wants_embedding persisted
```

# 9\. API Design

The Go Gateway exposes the public API surface and forwards authenticated requests to Python. The following are the MVP Python service endpoints.

| **Method** | **Endpoint**                  | **Purpose**                                   |
| ---------- | ----------------------------- | --------------------------------------------- |
| POST       | /profiles                     | Create a profile                              |
| GET        | /profiles/{user_id}           | Get a profile                                 |
| PATCH      | /profiles/{user_id}           | Update profile                                |
| POST       | /onboarding/session           | Start onboarding conversation                 |
| POST       | /onboarding/message           | Send an answer/message and advance onboarding |
| GET        | /onboarding/{conversation_id} | Get onboarding state/history                  |
| POST       | /matches                      | Create a matching job; returns job_id         |
| GET        | /matches/jobs/{job_id}        | Get matching job status/results               |
| GET        | /matches/{user_id}            | Read latest persisted matches/results         |

# 10\. Representative API Contracts

## POST /onboarding/session

```
Request:
{
  "user_id": "uuid"
}

Response:
{
  "conversation_id": "uuid",
  "message": "What are you looking for in a relationship right now?"
}
```

## POST /onboarding/message

```
Request:
{
  "conversation_id": "uuid",
  "message": "I'm looking for something serious..."
}

Response:
{
  "conversation_id": "uuid",
  "message": "What do you most need from a partner?",
  "status": "in_progress"
}
```

## POST /matches

```
Request:
{
  "user_id": "uuid",
  "limit": 5
}

Response: HTTP 202
{
  "job_id": "uuid",
  "status": "pending"
}
```

## GET /matches/jobs/{job_id}

```
Response while running:
{
  "job_id": "uuid",
  "status": "running"
}

Response when complete:
{
  "job_id": "uuid",
  "status": "completed",
  "matches": [
    {
      "candidate_id": "uuid",
      "dimension_results": {...},
      "strong_alignments": [...],
      "potential_conflicts": [...],
      "uncertainties": [...]
    }
  ]
}
```

## GET /profiles/{user_id}

```
Response:
{
  "user_id": "uuid",
  "age": 23,
  "gender": "...",
  "orientation": "...",
  "location": {...},
  "relationship_goal": "...",
  "preferred_age_min": 21,
  "preferred_age_max": 27,
  "max_distance_km": 30,
  "profile": {
    "self": {...},
    "wants": {...},
    "constraints": {...},
    "contradictions": [...]
  }
}
```

# 11\. Database Schema

The MVP keeps the profile as one 1:1 entity. Deterministic fields stay typed for filtering; nuanced LLM-derived signals remain JSONB.

## profiles

```
profiles
├── user_id UUID PRIMARY KEY
├── age INT
├── gender TEXT
├── orientation TEXT
├── location GEOGRAPHY(Point, 4326)          -- or lat/lng for a simpler MVP
├── relationship_goal TEXT
├── preferred_age_min INT
├── preferred_age_max INT
├── max_distance_km INT
├── preferred_genders JSONB
├── required_relationship_goal TEXT
├── profile JSONB NOT NULL
├── self_embedding VECTOR(N)
├── wants_embedding VECTOR(N)
├── embedding_source_text JSONB
├── extraction_version TEXT
├── created_at TIMESTAMP
└── updated_at TIMESTAMP
```

## conversations

```
conversations
├── id UUID PRIMARY KEY
├── user_id UUID NOT NULL
├── state JSONB                         -- LangGraph/checkpoint state
├── status TEXT                         -- active/completed
├── created_at TIMESTAMP
└── updated_at TIMESTAMP

conversation_messages
├── id UUID PRIMARY KEY
├── conversation_id UUID NOT NULL
├── role TEXT                           -- user / assistant
├── content TEXT NOT NULL
├── question_id TEXT NULL
├── created_at TIMESTAMP
```

## jobs

```
jobs
├── id UUID PRIMARY KEY
├── user_id UUID NOT NULL
├── type TEXT NOT NULL                  -- matching / embedding
├── status TEXT NOT NULL                -- pending/running/completed/failed
├── payload JSONB
├── result JSONB NULL
├── attempts INT DEFAULT 0
├── error TEXT NULL
├── available_at TIMESTAMP
├── started_at TIMESTAMP NULL
├── completed_at TIMESTAMP NULL
├── created_at TIMESTAMP
└── updated_at TIMESTAMP
```

## compatibility_results

```
compatibility_results
├── id UUID PRIMARY KEY
├── user_a_id UUID NOT NULL
├── user_b_id UUID NOT NULL
├── dimension_results JSONB
├── strong_alignments JSONB
├── potential_conflicts JSONB
├── dealbreaker_violations JSONB
├── uncertainties JSONB
├── model_name TEXT
├── reasoning_version TEXT
├── created_at TIMESTAMP
└── updated_at TIMESTAMP

UNIQUE(user_a_id, user_b_id, reasoning_version)
```

## 12\. Profile JSONB Shape

```
{
  "self": {
    "values": [],
    "lifestyle": [],
    "personality_signals": [],
    "interests": [],
    "life_goals": [],
    "conflict_style": [],
    "provides": []
  },
  "wants": {
    "partner_traits": [],
    "emotional_needs": [],
    "relationship_expectations": [],
    "desired_lifestyle": [],
    "partner_values": []
  },
  "constraints": {
    "dealbreakers": []
  },
  "contradictions": []
}
```

## 13\. Evidence Model

```
{
  "label": "emotional_support",
  "summary": "Prefers listening before offering advice.",
  "evidence": {
    "quote": "I usually listen first rather than immediately trying to fix things.",
    "question_id": "q3"
  },
  "confidence": 0.91
}
```

Every extracted non-null claim should be traceable to source text. The application should validate that an evidence quote is actually present in the raw answer before persisting the claim. Unknown information should remain unknown rather than being invented by the model.

# 14\. Embedding Design

The MVP uses an external Hugging Face embedding API. The embedding model is separate from the compatibility LLM.

```
Profile JSONB
   |
   +--> self semantic text ----> Hugging Face Embedding API ----> self_embedding
   |
   +--> wants semantic text ---> Hugging Face Embedding API ----> wants_embedding
                                                               |
                                                               v
                                                        PostgreSQL/pgvector
```

- self_embedding represents what the person is like and what they offer.
- wants_embedding represents what the person wants from a partner.
- Use the same embedding model/configuration for vectors that will be compared.
- Persist embedding_source_text so retrieval can be debugged.
- Regenerate embeddings whenever the relevant structured profile changes.
- For MVP, embedding generation can be a worker job so CRUD does not wait on the external API.

# 15\. Retrieval Strategy

```
For user A:

1. SQL hard filters:
   age, location, gender/orientation, relationship goal,
   explicit deterministic constraints.

2. pgvector:
   A.wants_embedding
        ↓
   candidate.self_embedding

3. Return a recall-oriented shortlist.

4. Do not treat vector similarity as compatibility.
   Final compatibility is determined by pairwise reasoning.
```

Reciprocity is evaluated later: A wants -> B self and B wants -> A self. A candidate should not be rejected solely because the reverse vector direction is weak; the reasoning stage handles the richer pairwise relationship.

# 16\. Compatibility Agent Output

```
{
  "candidate_id": "uuid",
  "dimension_results": {
    "emotional_needs": {
      "verdict": "strong_alignment",
      "evidence_a": "...",
      "evidence_b": "..."
    },
    "conflict_style": {
      "verdict": "unclear",
      "evidence_a": "...",
      "evidence_b": null
    }
  },
  "strong_alignments": [],
  "potential_conflicts": [],
  "dealbreaker_violations": [],
  "uncertainties": []
}
```

Use categorical dimension verdicts such as strong_alignment, partial_alignment, unclear, and conflict. Avoid a single fake compatibility score. Evidence for a claimed alignment or conflict should come from both profiles.

# 17\. Worker Internals

```
while True:
    job = claim_next_pending_job()

    if not job:
        sleep(poll_interval)
        continue

    try:
        if job.type == "embedding":
            run_embedding_job(job)
        elif job.type == "matching":
            run_matching_job(job)

        mark_completed(job)

    except RetryableError as e:
        retry_or_fail(job, e)

    except Exception as e:
        mark_failed(job, e)
```

The exact worker implementation can begin as a simple polling loop. PostgreSQL row locking prevents multiple worker processes from claiming the same job. This is intentionally simpler than introducing a message broker for the MVP.

## 18\. Matching Worker Internals

```
run_matching_job(job):
    profile = load_profile(job.user_id)

    candidates = hard_filter_candidates(profile)

    candidates = vector_retrieve(
        query=profile.wants_embedding,
        pool=candidates,
        limit=100
    )

    candidates = optional_pre_rank(candidates, limit=20)

    for candidate in candidates:
        result = compatibility_agent.evaluate(profile, candidate)
        save_compatibility_result(result)

    rank_saved_results()
    return top_n
```

# 19\. Scaling Path

The MVP does not require Kafka or microservices. The important scalability boundary is already present: API and workers are separate processes. If load grows, API instances and worker instances can be scaled independently.

```
                 Load Balancer
                      |
             +--------+--------+
             |                 |
          API x N          Worker x M
             |                 |
             +--------+--------+
                      |
                PostgreSQL
                 + pgvector

Later, if genuinely needed:
Worker -> queue -> specialized workers
Embedding worker -> dedicated inference service
Compatibility worker -> independently scaled LLM workload
```

This keeps the MVP simple without locking the system into a single-process design. The code modules also provide natural boundaries if an expensive workload eventually needs to become its own service.

# 20\. Recommended MVP Build Order

1. Freeze PostgreSQL + pgvector schema.
2. Implement FastAPI profile CRUD.
3. Implement onboarding conversation state and LangGraph extraction.
4. Add evidence/confidence validation and capped follow-ups.
5. Implement Hugging Face embedding client and embedding jobs.
6. Implement hard-filter SQL queries.
7. Implement pgvector retrieval.
8. Implement compatibility reasoning agent with strict structured output.
9. Implement matching jobs and worker process.
10. Persist and expose compatibility results.
11. Build synthetic evaluation profiles and measure retrieval/reasoning quality.

# 21\. MVP Design Principles

- Frontend talks only to the Go Gateway.
- Go Gateway handles routing/auth; Python owns Belong domain logic.
- FastAPI remains thin.
- CRUD and long-running workflows share one Python codebase but run in separate processes.
- PostgreSQL is the source of truth; pgvector handles semantic retrieval.
- LLMs extract and reason; SQL handles deterministic constraints.
- Vector similarity is retrieval, not final compatibility.
- Do not invent profile traits when evidence is missing.
- Use jobs for matching and embedding work so clients do not wait on long workflows.
- Do not add Kafka/microservices until there is a measured need.

# 22\. Final MVP Architecture

```
Frontend
   |
   v
Go API Gateway
   |
   +---------------------> Go Auth Service ---> Auth DB
   |
   v
Python Belong Service
   |
   +-- FastAPI API Process
   |      |
   |      +-- Profile CRUD
   |      +-- Onboarding message/status
   |      +-- Job creation/status
   |      +-- Profile/match reads
   |
   +-- Worker Process
   |      |
   |      +-- Onboarding/embedding jobs
   |      +-- Matching jobs
   |      +-- Compatibility Agent
   |
   +------------------------------+
                                  |
                                  v
                         PostgreSQL + pgvector
                                  |
                         +--------+--------+
                         |                 |
                     LLM API      Hugging Face
                                  Embedding API
```