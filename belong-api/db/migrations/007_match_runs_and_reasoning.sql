-- Migration 007: Create match_runs table and extend compatibility_results with match_id and overall_reasoning

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

-- 4. Create new indices for fast lookups & active pair filtering
CREATE INDEX IF NOT EXISTS idx_compatibility_match_id ON compatibility_results(match_id);
CREATE INDEX IF NOT EXISTS idx_compatibility_user_a_latest ON compatibility_results(user_a_id, is_latest) WHERE is_latest = true;
