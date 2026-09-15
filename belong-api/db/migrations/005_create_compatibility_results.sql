-- Belong Migration: 005_create_compatibility_results.sql
-- Description: Create compatibility_results table according to Section 11

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

-- Indexes for querying compatibility results by user
CREATE INDEX IF NOT EXISTS idx_compatibility_results_user_a ON compatibility_results (user_a_id);
CREATE INDEX IF NOT EXISTS idx_compatibility_results_user_b ON compatibility_results (user_b_id);
CREATE INDEX IF NOT EXISTS idx_compatibility_results_created_at ON compatibility_results (created_at);
