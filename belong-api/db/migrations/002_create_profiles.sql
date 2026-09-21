-- Belong Migration: 002_create_profiles.sql
-- Description: Create profiles table and semantic vector indexes according to Section 11

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

-- Index for HNSW cosine similarity search on self_embedding
CREATE INDEX IF NOT EXISTS idx_profiles_self_embedding 
ON profiles USING hnsw (self_embedding vector_cosine_ops);

-- Index for HNSW cosine similarity search on wants_embedding
CREATE INDEX IF NOT EXISTS idx_profiles_wants_embedding 
ON profiles USING hnsw (wants_embedding vector_cosine_ops);

-- Composite index for fast hard constraint SQL filtering
CREATE INDEX IF NOT EXISTS idx_profiles_filters 
ON profiles (gender, relationship_goal, age);

-- Index for geographic coordinates
CREATE INDEX IF NOT EXISTS idx_profiles_lat_lon 
ON profiles (latitude, longitude);
