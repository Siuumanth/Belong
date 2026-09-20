import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from uuid import uuid4, UUID

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("onboarding_simulation")

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PERSONAS_FILE = FIXTURES_DIR / "personas.json"


def load_personas() -> List[Dict[str, Any]]:
    """Loads synthetic personas from personas.json."""
    if not PERSONAS_FILE.exists():
        raise FileNotFoundError(f"Personas file not found at {PERSONAS_FILE}")
    with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("personas", [])


async def run_onboarding_for_persona(persona: Dict[str, Any], api_base_url: str = "http://localhost:8000"):
    """Simulates a full human onboarding conversation for a given persona against the API."""
    persona_id = persona["id"]
    responses: Dict[str, str] = persona.get("question_responses", {})
    user_id = str(uuid4())

    logger.info(f"--- Starting Onboarding Simulation for Persona '{persona_id}' (User ID: {user_id}) ---")

    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        # Step 1: Create Profile (Demographics)
        demo = persona.get("demographics", {})
        profile_payload = {
            "user_id": user_id,
            "age": demo.get("age", 25),
            "gender": demo.get("gender", "other"),
            "orientation": demo.get("orientation", "straight"),
            "latitude": demo.get("latitude", 37.7749),
            "longitude": demo.get("longitude", -122.4194),
            "relationship_goal": demo.get("relationship_goal", "long-term"),
            "preferred_age_min": demo.get("preferred_age_min", 21),
            "preferred_age_max": demo.get("preferred_age_max", 35),
            "max_distance_km": demo.get("max_distance_km", 50),
            "preferred_genders": demo.get("preferred_genders", []),
            "required_relationship_goal": demo.get("required_relationship_goal"),
            "profile": persona.get("profile", {})
        }

        # Create initial profile
        prof_res = await client.post("/profiles", json=profile_payload)
        if prof_res.status_code not in (200, 201):
            logger.error(f"Failed to create profile for {persona_id}: {prof_res.text}")
            return False
        logger.info(f"Profile created for {persona_id}")

        # Step 2: Start Onboarding Session
        start_res = await client.post("/onboarding/session", json={"user_id": user_id})
        if start_res.status_code != 201:
            logger.error(f"Failed to start onboarding session for {persona_id}: {start_res.text}")
            return False

        session_data = start_res.json()
        conversation_id = session_data["conversation_id"]
        logger.info(f"Started session {conversation_id}. First question: '{session_data['first_question']}'")

        # Step 3: Iterate through question responses
        q_keys = [
            "q1_intent_partner",
            "q2_emotional_needs",
            "q3_conflict_provides",
            "q4_lifestyle_values",
            "q5_personality",
            "q6_dealbreakers"
        ]

        status = "active"
        for q_key in q_keys:
            if status == "completed":
                break

            user_msg = responses.get(q_key, "I value communication and honesty.")
            logger.info(f"Sending response for [{q_key}]: '{user_msg[:60]}...'")

            msg_res = await client.post("/onboarding/message", json={
                "conversation_id": conversation_id,
                "message": user_msg
            })

            if msg_res.status_code != 200:
                logger.error(f"Failed sending message for {persona_id}: {msg_res.text}")
                return False

            reply_data = msg_res.json()
            status = reply_data.get("status", "active")
            assistant_reply = reply_data.get("assistant_response", "")
            logger.info(f"Assistant replied (status={status}): '{assistant_reply[:60]}...'")

        logger.info(f"--- Onboarding Completed for Persona '{persona_id}' (Status: {status}) ---\n")
        return True


async def main():
    personas = load_personas()
    logger.info(f"Loaded {len(personas)} synthetic personas from {PERSONAS_FILE}")

    success_count = 0
    for p in personas:
        try:
            ok = await run_onboarding_for_persona(p)
            if ok:
                success_count += 1
        except Exception as e:
            logger.error(f"Error running onboarding for persona '{p['id']}': {e}")

    logger.info(f"Simulation summary: {success_count}/{len(personas)} personas successfully completed onboarding.")


if __name__ == "__main__":
    asyncio.run(main())
