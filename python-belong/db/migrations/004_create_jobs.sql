-- Belong Migration: 004_create_jobs.sql
-- Description: Create jobs table for asynchronous worker task queue according to Section 11

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type TEXT NOT NULL,                   -- 'matching' or 'embedding'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB NULL,
    attempts INT NOT NULL DEFAULT 0,
    error TEXT NULL,
    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for worker polling and atomic claiming using SKIP LOCKED
CREATE INDEX IF NOT EXISTS idx_jobs_claim 
ON jobs (status, available_at, created_at);

-- Index for checking job status by user
CREATE INDEX IF NOT EXISTS idx_jobs_user_id 
ON jobs (user_id);
