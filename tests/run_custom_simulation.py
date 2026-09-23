"""
Custom User Simulation & Matching Test Script
==============================================
A fully configurable script to test custom user personas, AI onboarding dialogues,
embedding generation, and match outcomes against the Belong backend API.

USAGE:
    python tests/run_custom_simulation.py

HOW TO CUSTOMIZE:
    1. Edit the User Personas (USER_1_CONFIG, USER_2_CONFIG) below.
    2. Adjust the SIMULATION CONFIG flags (e.g. RUN_ONBOARDING, TRIGGER_MATCHING).
    3. Run the script!
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

# Ensure tests directory and root directory are in sys.path
TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(ROOT_DIR))

from simulators.user_simulator import UserSimulator, PersonaConfig

# Setup clean logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("custom_simulation")


# =====================================================================
# ⚙️ SIMULATION CONFIGURATION
# =====================================================================
# API endpoint: Use 8000 for direct API, or 9000 for API Gateway
API_URL = os.getenv("BELONG_API_URL", "http://localhost:8000")

# Flags to control execution steps
CREATE_PROFILES = True      # Step 1: POST /profiles
RUN_ONBOARDING = True       # Step 2: Multi-turn AI Onboarding chat
TRIGGER_EMBEDDINGS = True   # Step 3: Extract traits & embeddings
TRIGGER_MATCHING = True     # Step 4: Run vector search & LLM matching
POLL_TIMEOUT_SECS = 90      # Max seconds to wait for matching job to finish




# =====================================================================
# 👤 DEFINE YOUR TEST USER PERSONAS HERE
# =====================================================================

# USER 1: Custom Persona
USER_1_CONFIG = (
    PersonaConfig.builder("custom_user_alice")
    .with_name("Alice")
    .with_category("test_custom")
    .with_age(28, preferred_min=24, preferred_max=35)
    .with_gender("female", preferred_genders=["male"])
    .with_location(latitude=37.7749, longitude=-122.4194, max_distance_km=50)  # San Francisco
    .with_relationship_goal("long-term", required_goal="long-term")
    .with_responses(
        q1_intent_partner=(
            "honestly I'm just tired of situationships lol. I want someone who actually "
            "wants to build something real — like talks about the future, checks in on me, "
            "that kind of thing. communication is huge for me, and I need someone who's "
            "emotionally present, not just physically around."
        ),
        q2_emotional_needs=(
            "when I'm stressed I go pretty quiet and I need someone who notices and just... "
            "sits with me? not trying to fix it immediately. I really appreciate when my "
            "partner says something like 'I'm here' without me having to ask. words of "
            "affirmation are genuinely important to me, I feel more secure when I hear them."
        ),
        q3_conflict_provides=(
            "I don't like fighting but I won't avoid a hard conversation either. I usually "
            "take an hour or two to cool down first, then I'll bring it up. I try to say "
            "'I felt...' instead of blaming. when my partner is going through something, "
            "I show up — I cook for them, check in more often, just make sure they know "
            "I'm paying attention."
        ),
        q4_lifestyle_values=(
            "I do morning yoga most days, like 5-6 times a week. I work in product design "
            "so I spend a lot of time at a screen which is why I try to stay active. "
            "weekends are usually a hike or farmers market, maybe a bookstore. I'm "
            "plant-based and pretty into cooking. I care a lot about being consistent — "
            "like doing small things well over time."
        ),
        q5_personality=(
            "my friends say I'm a lot — in a good way I think? I'm pretty intense when "
            "I care about something, very organized, and I overthink sometimes but I'm "
            "self-aware about it. I'm warm and I genuinely love people. I probably make "
            "a good partner because I actually pay attention to the small stuff."
        ),
        q6_dealbreakers=(
            "smoking is a hard no, I have asthma. also anyone who uses substances "
            "regularly — I'm fine with a drink socially but that's about it. and "
            "dishonesty in any form, even white lies about small things. if I can't trust "
            "what you say, it's done."
        ),
    )
    .build()
)

# USER 2: Custom Candidate Persona
USER_2_CONFIG = (
    PersonaConfig.builder("custom_user_bob")
    .with_name("Bob")
    .with_category("test_custom")
    .with_age(30, preferred_min=23, preferred_max=32)
    .with_gender("male", preferred_genders=["female"])
    .with_location(latitude=37.7800, longitude=-122.4100, max_distance_km=50)  # Near SF
    .with_relationship_goal("long-term", required_goal="long-term")
    .with_responses(
        q1_intent_partner=(
            "I want something that actually lasts. I've had fun, I've dated around, "
            "but at this point I want someone I can genuinely grow with — someone who's "
            "curious, takes care of themselves, and doesn't play games. trust is the "
            "baseline for me, everything else builds from there."
        ),
        q2_emotional_needs=(
            "when I'm stressed I get kind of quiet and withdrawn — I usually need an hour "
            "to process before I can talk about it. what helps is if my partner doesn't "
            "push too hard but also doesn't disappear. just knowing they're around is "
            "enough. I'm the opposite when she's stressed — I'm pretty good at just "
            "listening without jumping to solutions."
        ),
        q3_conflict_provides=(
            "I try to deal with things pretty quickly rather than letting them sit. "
            "I stay calm, I don't raise my voice — I just hate that. I'd rather have "
            "a slightly awkward conversation than let something fester for a week. "
            "I think I'm good at making my partner feel stable, like I'm not going anywhere "
            "even when things are hard."
        ),
        q4_lifestyle_values=(
            "trail running is my thing — I do a half marathon most weekends. I'm a software "
            "engineer so weekdays are pretty heads-down but I try to get outside every day. "
            "I got into coffee brewing during covid and now I take it a bit too seriously. "
            "I value people who actually have ambition and keep growing, professionally "
            "or personally, I don't really care which."
        ),
        q5_personality=(
            "pretty chill, pretty reliable. I show up when I say I will. I'm curious about "
            "a lot of things — I'll read a book about almost anything. my friends say I'm "
            "a good listener which I think is true, I genuinely care what people have to say. "
            "I can be a bit reserved at first but I warm up fast."
        ),
        q6_dealbreakers=(
            "I can't do arrogance, like someone who can never admit they're wrong. "
            "and dishonesty — not just big lies, the small habitual ones are worse honestly. "
            "also someone who's totally stagnant, just not interested in improving anything "
            "about themselves."
        ),
    )
    .build()
)


# =====================================================================
# 🚀 SIMULATION RUNNER ENGINE
# =====================================================================

async def check_api_health(client: httpx.AsyncClient) -> bool:
    """Verifies backend API service is running and healthy."""
    try:
        res = await client.get("/healthz")
        if res.status_code == 200:
            logger.info(f"Connected to Belong API at {API_URL} (Status: OK)")
            return True
        logger.error(f"API health check failed with status {res.status_code}")
        return False
    except Exception as e:
        logger.error(f"Cannot connect to Belong API at {API_URL}: {e}")
        logger.error("Make sure your API server is running (e.g. docker compose up or uvicorn main:app).")
        return False


async def poll_job_completion(client: httpx.AsyncClient, job_id: str, max_secs: int = 30) -> bool:
    """Polls async matching job status until completed or timed out."""
    logger.info(f"Polling matching job '{job_id}' (max {max_secs}s)...")
    elapsed = 0
    interval = 2
    while elapsed < max_secs:
        await asyncio.sleep(interval)
        elapsed += interval
        try:
            res = await client.get(f"/api/matches/jobs/{job_id}")
            if res.status_code == 200:
                data = res.json()
                status = data.get("status", "unknown")
                logger.info(f"  └─ Job status after {elapsed}s: {status}")
                if status == "completed":
                    return True
                elif status == "failed":
                    logger.error(f"  └─ Job failed: {data.get('error', 'No error detail')}")
                    return False
            else:
                logger.warning(f"  └─ Unexpected status code {res.status_code} polling job")
        except Exception as e:
            logger.warning(f"  └─ Error polling job: {e}")

    logger.warning("Job polling timed out before completion.")
    return False


async def run_simulation():
    """Main execution workflow."""
    print("=" * 70)
    print("      BELONG CUSTOM USER SIMULATION RUNNER")
    print("=" * 70)

    sim_user_1 = UserSimulator(USER_1_CONFIG)
    sim_user_2 = UserSimulator(USER_2_CONFIG)
    users = [sim_user_1, sim_user_2]

    async with httpx.AsyncClient(base_url=API_URL, timeout=120.0) as client:

        # Health check
        if not await check_api_health(client):
            return

        # -----------------------------------------------------------------
        # STEP 1: CREATE PROFILES
        # -----------------------------------------------------------------
        if CREATE_PROFILES:
            print("\n-----------------------------------------------------------------")
            print("STEP 1: Registering User Demographic Profiles")
            print("-----------------------------------------------------------------")
            for user in users:
                ok = await user.create_profile_async(client)
                if ok:
                    logger.info(f"✅ Created profile for '{user.persona.id}' (User ID: {user.user_id})")
                else:
                    logger.error(f"❌ Failed creating profile for '{user.persona.id}'")

        # -----------------------------------------------------------------
        # STEP 2: MULTI-TURN AI ONBOARDING CHAT (Primary User Only)
        # -----------------------------------------------------------------
        if RUN_ONBOARDING:
            print("\n-----------------------------------------------------------------")
            print("STEP 2: Executing Multi-Turn AI Onboarding Dialogue (All Users)")
            print("-----------------------------------------------------------------")
            for user in users:
                logger.info(f"Starting conversational onboarding for '{user.persona.id}'...")
                ok = await user.run_onboarding_async(client)
                if ok:
                    logger.info(f"✅ Onboarding finished for '{user.persona.id}' (Status: {user.status})")
                else:
                    logger.error(f"❌ Onboarding failed/incomplete for '{user.persona.id}'")

        # -----------------------------------------------------------------
        # STEP 3: TRIGGER EMBEDDING GENERATION
        # -----------------------------------------------------------------
        if TRIGGER_EMBEDDINGS:
            print("\n-----------------------------------------------------------------")
            print("STEP 3: Triggering Trait & Vector Embedding Generation")
            print("-----------------------------------------------------------------")
            for user in users:
                ok = await user.trigger_embeddings_async(client)
                if ok:
                    logger.info(f"✅ Embeddings job queued for '{user.persona.id}'")
                else:
                    logger.error(f"❌ Embedding trigger failed for '{user.persona.id}'")

            logger.info("Waiting 5s for background EmbeddingWorker to process vectors in PostgreSQL...")
            await asyncio.sleep(5)

        # -----------------------------------------------------------------
        # STEP 4: TRIGGER MATCHING & FETCH RESULTS
        # -----------------------------------------------------------------

        if TRIGGER_MATCHING:
            print("\n-----------------------------------------------------------------")
            print("STEP 4: Triggering Compatibility Match Engine")
            print("-----------------------------------------------------------------")
            target_user = sim_user_1
            logger.info(f"Requesting matches for primary user '{target_user.persona.id}'...")
            job_id = await target_user.request_matches_async(client)

            if job_id:
                logger.info(f"✅ Match job successfully submitted! Job ID: {job_id}")

                # Poll for completion
                job_ok = await poll_job_completion(client, job_id, max_secs=POLL_TIMEOUT_SECS)

                # Fetch matches regardless
                print("\n-----------------------------------------------------------------")
                print(f"STEP 5: Fetching Match Results for User '{target_user.persona.id}'")
                print("-----------------------------------------------------------------")
                res = await client.get(f"/api/matches/{target_user.user_id}")

                if res.status_code == 200:
                    matches_data = res.json()
                    matches = matches_data.get("matches", [])
                    logger.info(f"Total Matches Returned: {len(matches)}")
                    print("\nMATCH RESULTS SUMMARY:")
                    print(json.dumps(matches_data, indent=2))
                else:
                    logger.error(f"Failed to fetch matches (Status Code: {res.status_code})")
                    logger.error(res.text)
            else:
                logger.error("❌ Failed to request match job.")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_simulation())
