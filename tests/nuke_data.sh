#!/usr/bin/env bash
# ==============================================================================
# Belong Platform - PostgreSQL Data Wipe Script
# ==============================================================================
# Wipes all user profiles, conversations, messages, async jobs, and match results
# from the PostgreSQL database while preserving database schema & structure.
#
# USAGE:
#     bash tests/nuke_data.sh
# ==============================================================================

set -e

CONTAINER_NAME="${POSTGRES_CONTAINER:-belong-postgres}"
DB_USER="${POSTGRES_USER:-belong_user}"
DB_NAME="${POSTGRES_DB:-belong}"

echo "=================================================================="
echo "🔥 NUKING ALL BELONG POSTGRESQL DATA..."
echo "=================================================================="

# Check if docker container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Error: Docker container '${CONTAINER_NAME}' is not running."
    echo "Please start services with: docker compose up -d"
    exit 1
fi

# Truncate all data tables with CASCADE
docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
    TRUNCATE TABLE 
        profiles, 
        conversations, 
        conversation_messages, 
        jobs, 
        compatibility_results 
    RESTART IDENTITY CASCADE;
"

echo "✅ SUCCESS: All PostgreSQL data tables have been nuked clean!"
echo "=================================================================="
