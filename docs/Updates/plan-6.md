# Matching Engine & Schema Architecture Refactor Plan

This plan details the implementation steps to refactor the Belong matching engine database schema, LLM output model, worker persistence logic, and profile inspection endpoints on branch `match-refactor`.

---

## 1. Overview & Key Objectives

1. **Batch Session Tracking (`match_runs` Table)**:
   - Introduce a `match_runs` table so each "Match" button click creates 1 match run entry (`match_id`).
   - Track status (`pending`, `completed`, `failed`), `candidate_count`, and execution timing.

2. **Historical Comparison Lineage (`compatibility_results` Refactor)**:
   - Link each compatibility comparison to a `match_id` via Foreign Key.
   - Add `is_latest` boolean flag to easily query active matches while keeping historical runs intact.
   - Add `overall_reasoning` text column for the LLM's executive conclusion paragraph.

3. **LLM Structured Output Update**:
   - Update `PairwiseCompatibilityOutput` schema in both `belong-workers` and `belong-api` to include `overall_reasoning`.

4. **User Profile & Signal Graph Inspection Endpoint**:
   - Ensure a dedicated API endpoint (`GET /api/profiles/me`) returns demography + extracted signal graph (`self`, `wants`, `constraints`).

---

## 2. Database Schema Changes (PostgreSQL Migration)

### Step 2.1: Create Migration Script `sql/004_match_runs_and_reasoning.sql`

```sql
-- 1. Create match_runs table for tracking matching job sessions
CREATE TABLE IF NOT EXISTS match_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    candidate_count INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_match_runs_user ON match_runs(user_id, created_at DESC);

-- 2. Modify compatibility_results table
ALTER TABLE compatibility_results
    ADD COLUMN IF NOT EXISTS match_id UUID REFERENCES match_runs(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS overall_reasoning TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS is_latest BOOLEAN NOT NULL DEFAULT true;

-- 3. Drop old unique constraint that enforced 1 row per pair version
ALTER TABLE compatibility_results DROP CONSTRAINT IF EXISTS uq_compatibility_pair_version;

-- 4. Create new indices for fast lookups & unique active pair index
CREATE INDEX IF NOT EXISTS idx_compatibility_match_id ON compatibility_results(match_id);
CREATE INDEX IF NOT EXISTS idx_compatibility_user_a_latest ON compatibility_results(user_a_id, is_latest) WHERE is_latest = true;
```

---

## 3. Pydantic Schema Updates

### File 1: `belong-workers/matching/schemas.py`
### File 2: `belong-api/matching/schemas.py`

Update `PairwiseCompatibilityOutput` to include `overall_reasoning`:

```python
class PairwiseCompatibilityOutput(BaseModel):
    overall_verdict: str = Field(
        ..., 
        description="Overall verdict: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'"
    )
    overall_reasoning: Optional[str] = Field(
        default="",
        description="2-3 sentence executive summary explaining why these two users match or don't match."
    )
    dimension_results: DimensionResults
    complementary_alignments: List[str] = Field(default_factory=list)
    shared_alignments: List[str] = Field(default_factory=list)
    potential_conflicts: List[str] = Field(default_factory=list)
    dealbreaker_violations: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    reciprocity_score: float = Field(default=0.0)
```

---

## 4. Worker Pipeline Updates (`belong-workers`)

### Step 4.1: Update Matching Execution Flow (`workers/matching_worker.py`)

1. **Job Initialization**:
   - Create a record in `match_runs` with `id = job_id`, `user_id = user_id`, `status = 'processing'`.

2. **Flag Maintenance**:
   - Before inserting new compatibility results for `user_a_id`, mark previous records for matching candidate pairs as `is_latest = false`:
     ```sql
     UPDATE compatibility_results 
     SET is_latest = false 
     WHERE user_a_id = $1 AND user_b_id = $2 AND is_latest = true;
     ```

3. **Persistence**:
   - Insert new rows into `compatibility_results` linking `match_id`, `overall_reasoning`, and setting `is_latest = true`.

4. **Job Completion**:
   - Update `match_runs` record status to `'completed'` and set `candidate_count = len(ranked_candidates)`, `completed_at = CURRENT_TIMESTAMP`.

---

## 5. API Endpoints Updates (`belong-api`)

### Step 5.1: Update Matches API (`api/routes/matches.py`)
- `POST /api/matches`: Creates `match_runs` record and pushes job to queue.
- `GET /api/matches`: Queries active matches using `WHERE user_a_id = $1 AND is_latest = true`.
- `GET /api/matches/history`: Queries past matching runs from `match_runs` table.

### Step 5.2: User Profile Signal Inspection (`api/routes/profiles.py`)
- Ensure `GET /api/profiles/me` returns both flat demographic fields and the full structured signal graph (`self`, `wants`, `constraints`).

---

## 6. Implementation Checklist & Order of Work

| Phase | Description | Task Details |
| :--- | :--- | :--- |
| **Phase 1** | Database Migration | Apply SQL migration script for `match_runs` and `compatibility_results` alterations. |
| **Phase 2** | Schema & Prompt Sync | Update Pydantic schemas in `belong-workers` and `belong-api` with `overall_reasoning`. |
| **Phase 3** | Worker Pipeline | Update `matching_worker.py` to manage `match_runs` lifecycle and `is_latest` flags. |
| **Phase 4** | API Routes | Update `matches.py` and `profiles.py` in `belong-api`. |
| **Phase 5** | End-to-End Verification | Re-run matching via API and verify database state across `match_runs` and `compatibility_results`. |

---

## 7. Verification Commands

```bash
# 1. Run Migration in Postgres
docker exec -i belong-postgres psql -U belong_user -d belong < sql/004_match_runs_and_reasoning.sql

# 2. Re-create containers to load updated code
docker compose up -d --force-recreate belong-workers belong-api

# 3. Trigger matching job via REST API
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/matches" -Headers @{"X-User-ID"="8073a6d4-0a55-4320-bce4-d7095d7f6b01"}

# 4. Inspect DB rows
docker exec belong-postgres psql -U belong_user -d belong -c "SELECT * FROM match_runs;"
docker exec belong-postgres psql -U belong_user -d belong -c "SELECT id, match_id, user_a_id, user_b_id, is_latest, overall_reasoning FROM compatibility_results;"
```
