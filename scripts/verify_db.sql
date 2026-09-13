-- Belong Database Verification Script

\echo '========================================='
\echo 'Checking PostgreSQL and pgvector Status'
\echo '========================================='

-- Check installed extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pgcrypto');

\echo ''
\echo '========================================='
\echo 'Checking Tables'
\echo '========================================='

SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

\echo ''
\echo '========================================='
\echo 'Checking Vector Columns in profiles'
\echo '========================================='

SELECT column_name, data_type, udt_name 
FROM information_schema.columns 
WHERE table_name = 'profiles' AND column_name LIKE '%embedding%';

\echo ''
\echo '========================================='
\echo 'Checking Indexes (including HNSW)'
\echo '========================================='

SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
ORDER BY tablename, indexname;

\echo ''
\echo '========================================='
\echo 'Testing Vector Cosine Similarity Search'
\echo '========================================='

-- Test vector distance operator (<=> is cosine distance in pgvector)
SELECT '[1, 0, 0]'::vector(3) <=> '[0, 1, 0]'::vector(3) AS orthogonal_cosine_distance,
       '[1, 0, 0]'::vector(3) <=> '[1, 0, 0]'::vector(3) AS identical_cosine_distance;

\echo ''
\echo 'Database is ready and verified!'
