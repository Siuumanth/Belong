-- Belong Migration: 001_init_extensions.sql
-- Description: Initialize required PostgreSQL extensions (pgvector and UUID generators)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
