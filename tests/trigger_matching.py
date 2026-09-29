"""
Trigger Matching Jobs for Profiles
==================================
Creates matching jobs for all profiles that have embeddings but no compatibility results.

Usage:
    python tests/trigger_matching.py [--all]
    
    --all: Create matching jobs for ALL profiles, not just those without results
"""

import asyncio
import sys
import logging
from pathlib import Path
from uuid import UUID

# Add belong-api directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "belong-api"))

from db.connection import get_db_connection
from jobs.repository import job_repository
from psycopg.rows import dict_row

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trigger_matching")


async def get_profiles_needing_matches(all_profiles: bool = False):
    """Fetch profiles that need matching jobs."""
    async with get_db_connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            if all_profiles:
                # Get all profiles with embeddings
                query = """
                    SELECT user_id, name
                    FROM profiles
                    WHERE self_embedding IS NOT NULL 
                      AND wants_embedding IS NOT NULL
                    ORDER BY created_at DESC
                """
            else:
                # Get profiles that have no compatibility results
                query = """
                    SELECT p.user_id, p.name
                    FROM profiles p
                    WHERE p.self_embedding IS NOT NULL 
                      AND p.wants_embedding IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM compatibility_results cr
                          WHERE cr.user_a_id = p.user_id OR cr.user_b_id = p.user_id
                      )
                    ORDER BY p.created_at DESC
                """
            
            await cur.execute(query)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def create_matching_jobs(profiles: list):
    """Create matching jobs for given profiles."""
    created = 0
    failed = 0
    
    for profile in profiles:
        raw_id = profile["user_id"]
        user_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        name = profile.get("name", "Unknown")
        
        try:
            job_data = await job_repository.create_job(
                user_id=user_id,
                job_type="matching",
                payload={"user_id": str(user_id)}
            )
            logger.info(f"✓ Created matching job {job_data['id']} for user {name} ({user_id})")
            created += 1
        except Exception as e:
            logger.error(f"✗ Failed to create matching job for user {name} ({user_id}): {e}")
            failed += 1
    
    return created, failed


async def main():
    all_profiles = "--all" in sys.argv
    
    logger.info("Fetching profiles needing matching jobs...")
    profiles = await get_profiles_needing_matches(all_profiles)
    
    if not profiles:
        logger.info("No profiles found needing matching jobs.")
        return
    
    logger.info(f"Found {len(profiles)} profiles needing matching")
    for p in profiles:
        logger.info(f"  - {p.get('name', 'Unknown')} ({p['user_id']})")
    
    auto_yes = "--yes" in sys.argv or "-y" in sys.argv
    if not auto_yes:
        print("\nCreate matching jobs for these profiles? [y/N]: ", end="")
        confirm = input().strip().lower()
        if confirm != 'y':
            logger.info("Cancelled.")
            return
    
    logger.info("Creating matching jobs...")
    created, failed = await create_matching_jobs(profiles)
    
    logger.info(f"\n✓ Created {created} matching jobs")
    if failed:
        logger.warning(f"✗ Failed to create {failed} jobs")
    
    logger.info("\nNote: Jobs will be processed by the worker. Check job status with:")
    logger.info("  docker exec -i belong-postgres psql -U belong_user -d belong -c \"SELECT id, user_id, type, status FROM jobs ORDER BY created_at DESC LIMIT 10;\"")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
