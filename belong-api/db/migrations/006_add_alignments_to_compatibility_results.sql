-- Belong Migration: 006_add_alignments_to_compatibility_results.sql
-- Description: Add complementary_alignments and shared_alignments JSONB columns to compatibility_results

ALTER TABLE compatibility_results 
ADD COLUMN IF NOT EXISTS complementary_alignments JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE compatibility_results 
ADD COLUMN IF NOT EXISTS shared_alignments JSONB NOT NULL DEFAULT '[]'::jsonb;
