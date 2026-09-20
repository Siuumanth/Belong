"""
Human Onboarding Simulation CLI Runner
======================================
CLI runner utilizing the UserSimulator actor engine to run multi-turn onboarding
simulations against a running belong-api service.

Usage:
    python tests/run_onboarding_simulation.py
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

import httpx

from simulators.user_simulator import UserSimulator, PersonaConfig

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


async def main():
    personas_raw = load_personas()
    logger.info(f"Loaded {len(personas_raw)} synthetic personas from {PERSONAS_FILE}")

    api_url = "http://localhost:8000"
    success_count = 0

    async with httpx.AsyncClient(base_url=api_url, timeout=30.0) as client:
        # Check API health
        try:
            health = await client.get("/healthz")
            if health.status_code != 200:
                logger.error(f"Belong API service returned status {health.status_code}")
                return
        except Exception as e:
            logger.error(f"Cannot connect to Belong API at {api_url}: {e}")
            return

        for p_dict in personas_raw:
            config = PersonaConfig.from_dict(p_dict)
            user = UserSimulator(config)

            logger.info(f"--- Starting Onboarding for Persona '{config.id}' (User ID: {user.user_id}) ---")

            # 1. Create Profile
            if not await user.create_profile_async(client):
                logger.error(f"Profile creation failed for {config.id}")
                continue

            # 2. Run Onboarding Simulation
            if await user.run_onboarding_async(client):
                logger.info(f"Onboarding successfully completed for '{config.id}'")
                success_count += 1
            else:
                logger.error(f"Onboarding failed or incomplete for '{config.id}'")

    logger.info(f"Simulation summary: {success_count}/{len(personas_raw)} personas completed onboarding successfully.")


if __name__ == "__main__":
    asyncio.run(main())
