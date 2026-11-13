# 04. Database & Storage Design

> **PostgreSQL 16, pgvector, and JSONB Architecture**  
> *Relational data integrity, semi-structured psychological signals, HNSW vector indexing, and atomic job reconciliation.*

---

## 1. Complete Database Entity-Relationship (ER) Diagram

Belong uses a single PostgreSQL 16 cluster with `uuid-ossp` and `pgvector` extensions enabled.

```
+----------------------------------------------------------------------------------------------------+
|                                    BELONG DATABASE SCHEMA                                          |
+----------------------------------------------------------------------------------------------------+

     +-------------------------+
     |          users          |
     +-------------------------+
     | id: UUID (PK)           |
     | username: TEXT (UQ)     |
     | email: TEXT (UQ)        |
     | password_hash: TEXT     |
     | created_at: TIMESTAMP   |
     +------------+------------+
                  |
                  | 1 : 1 (by user_id UUID)
                  v
     +-------------------------------------------------------------------------------+
     |                                    profiles                                   |
     +-------------------------------------------------------------------------------+
     | user_id: UUID (PK)                                                            |
     | name: TEXT, age: INT, gender: TEXT, orientation: TEXT                         |
     | latitude: FLOAT8, longitude: FLOAT8, max_distance_km: INT                     |
     | relationship_goal: TEXT, required_relationship_goal: TEXT                     |
     | preferred_age_min: INT, preferred_age_max: INT                                 |
     | preferred_genders: JSONB (Default '[]')                                       |
     | profile: JSONB (Default '{}' - Structured self/wants/constraints/signals)     |
     | self_embedding: VECTOR(384) (HNSW Cosine Indexed)                             |
     | wants_embedding: VECTOR(384) (HNSW Cosine Indexed)                            |
     | embedding_source_text: JSONB (Default '{}' - Canonical self_text & wants_text)  |
     | extraction_version: TEXT, created_at: TIMESTAMPTZ, updated_at: TIMESTAMPTZ    |
     +------------------+-----------------------------+-------------------------------+
                        |                             |
       1 : N            |                             | 1 : N
       (by user_id)     |                             | (by user_id)
       v                v                             v
+-----------------------------+               +-----------------------------+
|        conversations        |               |            jobs             |
+-----------------------------+               +-----------------------------+
| id: UUID (PK)               |               | id: UUID (PK)               |
| user_id: UUID               |               | user_id: UUID               |
| status: TEXT ('active'/'..')|               | type: TEXT ('embedding'/..) |
| current_area_index: INT     |               | status: TEXT ('pending'/..) |
| follow_up_count: INT (<=2)  |               | payload: JSONB              |
| covered_areas: JSONB        |               | result: JSONB               |
| extracted_signals: JSONB    |               | attempts: INT (Default 0)   |
| created_at, updated_at      |               | error: TEXT                 |
+--------------+--------------+               | available_at: TIMESTAMPTZ   |
               |                              | started_at, completed_at    |
               | 1 : N (CASCADE)              +-----------------------------+
               v
+-----------------------------+               +-----------------------------+
|    conversation_messages    |               |         match_runs          |
+-----------------------------+               +-----------------------------+
| id: UUID (PK)               |               | id: UUID (PK)               |
| conversation_id: UUID (FK)  |               | user_id: UUID (FK profiles) |
| role: TEXT ('user'/'asst')  |               | status: TEXT ('processing') |
| content: TEXT               |               | candidate_count: INT        |
| question_id: TEXT           |               | error_message: TEXT         |
| created_at: TIMESTAMPTZ     |               | created_at, completed_at    |
+-----------------------------+               +--------------+--------------+
                                                             |
                                                             | 1 : N (SET NULL)
                                                             v
                              +--------------------------------------------------------------+
                              |                    compatibility_results                     |
                              +--------------------------------------------------------------+
                              | id: UUID (PK)                                                |
                              | match_id: UUID (FK match_runs)                               |
                              | user_a_id: UUID, user_b_id: UUID                             |
                              | overall_verdict: TEXT ('strong_alignment' / 'conflict' / ..) |
                              | overall_reasoning: TEXT                                      |
                              | dimension_results: JSONB                                     |
                              | strong_alignments: JSONB, complementary_alignments: JSONB    |
                              | shared_alignments: JSONB, potential_conflicts: JSONB         |
                              | dealbreaker_violations: JSONB, uncertainties: JSONB          |
                              | model_name: TEXT, reasoning_version: TEXT                    |
                              | is_latest: BOOLEAN (Default TRUE)                            |
                              | created_at, updated_at: TIMESTAMPTZ                          |
                              +--------------------------------------------------------------+
```

---

## 2. Table-by-Table Technical Breakdown

### 1. `profiles` Table
The central entity of Belong. Combines relational demographic filters, document-based psychological signals, and mathematical vector coordinates:

```sql
CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    age INT,
    gender TEXT,
    orientation TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    relationship_goal TEXT,
    preferred_age_min INT,
    preferred_age_max INT,
    max_distance_km INT,
    preferred_genders JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_relationship_goal TEXT,
    profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    self_embedding VECTOR(384),
    wants_embedding VECTOR(384),
    embedding_source_text JSONB NOT NULL DEFAULT '{}'::jsonb,
    extraction_version TEXT NOT NULL DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 2. `conversations` & `conversation_messages`
Stores the multi-turn conversational onboarding session:
* `conversations`: Holds active state machine progression (`current_area_index`, `follow_up_count`, `covered_areas`).
* `conversation_messages`: Verbatim chat transcript. Uses `ON DELETE CASCADE` so deleting a conversation automatically purges all child messages.

### 3. `jobs` Table (Task Queue & Reconciler)
Backed by an index specifically optimized for atomic job claiming:
```sql
CREATE INDEX IF NOT EXISTS idx_jobs_claim 
ON jobs (status, available_at, created_at);
```
Used by background workers to claim unacknowledged pending jobs via:
```sql
SELECT id, user_id, type, payload FROM jobs
WHERE status = 'pending' AND available_at <= CURRENT_TIMESTAMP AND attempts < 3
ORDER BY created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

### 4. `compatibility_results` & `match_runs`
* `match_runs`: Tracks a matching computation session for a user (`status`, `candidate_count`, `completed_at`).
* `compatibility_results`: Contains the deep qualitative output for evaluated pairs.
* **Partial Indexing Optimization:**
  ```sql
  CREATE INDEX IF NOT EXISTS idx_compatibility_user_a_latest 
  ON compatibility_results(user_a_id, is_latest) 
  WHERE is_latest = true;
  ```
  *Why this matters:* Users accumulate historical match evaluations across multiple runs. When displaying matches on the frontend, queries only request `is_latest = true`. A **partial index** indexes only active records, keeping the index small, cache-friendly, and ultra-fast.

---

## 3. Why JSONB for Profile Signals?

Interviewers will ask: *"Why store extracted traits in JSONB instead of normalized relational tables (`traits`, `user_traits`, `evidence`)?"*

### 1. Schema Flexibility for Emergent AI Signals
* Human psychology does not fit neatly into static relational columns. Different users reveal completely different categories of traits (one user discusses attachment trauma; another discusses work-life schedule and pets).
* Unmapped or novel insights discovered by the LLM (`novel_signals`) can be stored dynamically without requiring database migrations (`ALTER TABLE`).

### 2. Document Atomicity & Read Performance
* During candidate retrieval and pairwise LLM reasoning, the system needs the **entire psychological profile at once**.
* In a normalized relational schema with 8 joined tables (`user_values`, `user_provides`, `user_needs`, `user_dealbreakers`, `evidence_quotes`), retrieving 15 candidates requires massive SQL joins across thousands of rows.
* In JSONB, the entire profile is read in a single point lookup with zero table joins:
  ```json
  {
    "self": {
      "values": [{ "label": "Honesty", "quote": "...", "confidence": 0.95 }],
      "provides": [{ "label": "Emotional grounding", "quote": "...", "confidence": 0.92 }]
    },
    "wants": {
      "partner_traits": [{ "label": "Patient listener", "quote": "...", "confidence": 0.9 }]
    },
    "constraints": {
      "dealbreakers": [{ "label": "No smoking", "quote": "...", "confidence": 1.0 }]
    }
  }
  ```

### 3. Queryability in PostgreSQL
Unlike plain `JSON` (which stores text as-is), `JSONB` stores data in a parsed binary format:
* Fast containment checking (`@>`).
* Dynamic array unnesting (`jsonb_array_elements_text(p.preferred_genders)`).
* Allows indexing on nested keys using GIN (Generalized Inverted Index) if needed.

---

## 4. `pgvector` Mechanics: Dimensions, Operators & HNSW Indexing

### Vector Dimension Selection: 384
* Output dimension of `sentence-transformers/all-MiniLM-L6-v2`.
* High enough to capture nuanced semantic meaning across relationship preferences.
* Compact enough for in-memory index caching ($384 \times 4 \text{ bytes} \approx 1.5 \text{ KB}$ per vector).

### Distance Operators in `pgvector`:
| Operator | Distance Metric | Mathematical Formula | Usage in Belong |
| :---: | :---: | :---: | :--- |
| `<=>` | **Cosine Distance** | $1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$ | **Used exclusively** in Belong. Direction/orientation matters, not magnitude. |
| `<->` | **L2 (Euclidean)** | $\sqrt{\sum (u_i - v_i)^2}$ | Sensitive to vector length; not ideal for text semantic similarity. |
| `<#>` | **Negative Inner Product** | $-(u \cdot v)$ | Equivalent to cosine only if vectors are strictly pre-normalized. |

### HNSW vs. IVFFlat Indexes
Belong creates **HNSW** (Hierarchical Navigable Small World) indexes on vector columns:
```sql
CREATE INDEX idx_profiles_self_embedding 
ON profiles USING hnsw (self_embedding vector_cosine_ops);

CREATE INDEX idx_profiles_wants_embedding 
ON profiles USING hnsw (wants_embedding vector_cosine_ops);
```

#### Why HNSW Beats IVFFlat in Production:
1. **No Training Step Required:** IVFFlat requires clustering training data into Voronoi cells. If you build the index on an empty or small table, recall collapses as new users join unless you manually rebuild the index (`REINDEX`). HNSW builds its multi-layer graph incrementally with every `INSERT`.
2. **Superior Recall at Low Latency:** At 95%+ recall, HNSW executes queries in single-digit milliseconds, significantly faster than IVFFlat.
3. **No Lock Contention:** Works seamlessly with real-time updates when users complete onboarding.

---

## 5. RabbitMQ In-Memory Messages vs. PostgreSQL Persistent Records

Belong employs the **Transactional Outbox / Dual-Persistence Pattern**:

| Feature | RabbitMQ Message | PostgreSQL `jobs` Table |
| :--- | :--- | :--- |
| **Storage Medium** | In-memory RAM / Erlang mnesia | Disk-persisted WAL & relational tables |
| **Primary Purpose** | Real-time event routing & load leveling | Audit log, state recovery, and retry tracking |
| **Lifetime** | Deleted upon consumer `ACK` | Preserved permanently with timestamps & results |
| **Failure Behavior** | Dropped if broker crashes before unacknowledged persist | Survives full system power loss or server crash |

### The Worker Fail-Safe Mechanism (`reconcile_pending_jobs`):
In `belong-workers/main.py`:
1. Normal path: Worker consumes message directly from RabbitMQ queue in $< 5 \text{ ms}$.
2. Edge case: If RabbitMQ drops a connection or crashes during job dispatch, the message could be lost.
3. **The Reconciler:** A background loop runs every 15 seconds in the worker, issuing:
   ```sql
   UPDATE jobs
   SET status = 'running', started_at = CURRENT_TIMESTAMP, attempts = attempts + 1
   WHERE id = (
       SELECT id FROM jobs
       WHERE status = 'pending' AND available_at <= CURRENT_TIMESTAMP AND attempts < 3
       ORDER BY created_at ASC
       FOR UPDATE SKIP LOCKED
       LIMIT 1
   )
   RETURNING id, user_id, type, payload;
   ```
4. `FOR UPDATE SKIP LOCKED` ensures multiple worker instances never claim the same job, preventing race conditions without needing distributed Redis locks.

---

## 6. Tracing an Actual Record Through the Schema

### 1. User registers:
`users` table:
```text
id: 1f2fe223-49e9-44b8-894e-56baebb94d23
username: alice
email: alice@example.com
password_hash: $2a$10$N9qo8uLOickgx2ZMRZoMye...
```

### 2. User chats with AI Guide:
`conversations`:
```text
id: c7e1d52a-9f12-4e5a-8b1a-63d1ef9a8120
user_id: 1f2fe223-49e9-44b8-894e-56baebb94d23
status: completed
current_area_index: 5
follow_up_count: 1
```

`conversation_messages` (sample row):
```text
conversation_id: c7e1d52a-9f12-4e5a-8b1a-63d1ef9a8120
role: user
content: "I care a lot about honesty and clear communication, especially when resolving disagreements."
question_id: q1_intent_partner
```

### 3. Profile finalized & Vectors saved:
`profiles`:
```text
user_id: 1f2fe223-49e9-44b8-894e-56baebb94d23
name: Alice
age: 28, gender: female, relationship_goal: long-term
preferred_genders: ["male"]
profile: {"self": {"values": [...]}, "wants": {"partner_traits": [...]}}
self_embedding: [-0.0421, 0.0812, 0.0154, ... (384 floats)]
wants_embedding: [0.0194, -0.0521, 0.0911, ... (384 floats)]
```

### 4. Matching run initiated:
`match_runs`:
```text
id: m991a0b3-4412-4809-a1c2-771ef82a0011
user_id: 1f2fe223-49e9-44b8-894e-56baebb94d23
status: completed
candidate_count: 5
```

### 5. Evaluated candidate persisted:
`compatibility_results`:
```text
match_id: m991a0b3-4412-4809-a1c2-771ef82a0011
user_a_id: 1f2fe223-49e9-44b8-894e-56baebb94d23 (Alice)
user_b_id: 8e3b1201-71bc-4991-923f-110098aab002 (Bob)
overall_verdict: strong_alignment
overall_reasoning: "Both Alice and Bob prioritize transparent communication..."
dimension_results: {
  "emotional_needs": { "verdict": "strong_alignment", "evidence_a": [...], "evidence_b": [...] },
  "conflict_style": { "verdict": "strong_alignment", "evidence_a": [...], "evidence_b": [...] }
}
is_latest: true
```

