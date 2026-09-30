-- Migration 008: Add overall_verdict column to compatibility_results
ALTER TABLE compatibility_results
    ADD COLUMN IF NOT EXISTS overall_verdict TEXT NOT NULL DEFAULT 'unclear';
