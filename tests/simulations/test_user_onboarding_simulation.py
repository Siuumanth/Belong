"""
User Onboarding Simulation Test Suite
======================================
Simulates real human users undergoing multi-turn conversational onboarding dialogues.

Tests:
1. Standard persona onboarding simulation (loaded from personas.json).
2. Dynamic configurable user persona onboarding simulation.
3. Edge case onboarding (vague responses, custom dealbreakers).
"""

import os
import pytest
import httpx
from typing import Dict, Any, List

from simulators.user_simulator import UserSimulator, PersonaConfig


@pytest.mark.simulation
class TestUserOnboardingSimulation:
    """Test suite for simulating multi-turn user onboarding dialogues."""

    @pytest.fixture
    def api_url(self) -> str:
        return os.getenv("BELONG_API_URL", "http://localhost:8000")

    @pytest.mark.asyncio
    async def test_standard_persona_onboarding_simulation(
        self, golden_personas: List[Dict[str, Any]], api_url: str
    ):
        """Simulates full multi-turn onboarding for loaded golden personas."""
        if not golden_personas:
            pytest.skip("No golden personas found in fixtures.")

        # Test first persona (e.g. Alice)
        persona = PersonaConfig.from_dict(golden_personas[0])
        user = UserSimulator(persona)

        async with httpx.AsyncClient(base_url=api_url, timeout=15.0) as client:
            # Check if API is reachable
            try:
                health = await client.get("/healthz")
                if health.status_code != 200:
                    pytest.skip("Belong API microservice is not reachable.")
            except Exception:
                pytest.skip("Belong API microservice is not running on port 8000.")

            # 1. Create Profile
            profile_ok = await user.create_profile_async(client)
            assert profile_ok is True, f"Failed to create profile for user {user.user_id}"

            # 2. Run Multi-turn Onboarding
            onboarding_ok = await user.run_onboarding_async(client)
            assert onboarding_ok is True, f"Onboarding did not complete for user {user.user_id}"
            assert user.status == "completed"

    @pytest.mark.asyncio
    async def test_custom_configurable_user_onboarding(self, api_url: str):
        """
        Tests onboarding with a programmatically configured custom user persona
        (overriding age, location, and question responses).
        """
        # Create a dynamic custom persona via builder
        custom_persona = (
            PersonaConfig.builder("sim_user_custom_01")
            .with_category("test_custom")
            .with_age(27, preferred_min=24, preferred_max=32)
            .with_gender("female", preferred_genders=["male"])
            .with_location(37.7749, -122.4194, max_distance_km=25)
            .with_relationship_goal("long-term", required_goal="long-term")
            .with_responses(
                q1_intent_partner="I am seeking a partner for a deep, lifelong bond and family building.",
                q2_emotional_needs="I need active listening, emotional safety, and frequent check-ins.",
                q3_conflict_provides="I stay calm, listen patiently, and express my feelings transparently.",
                q4_lifestyle_values="Daily running, plant-based cooking, reading novels, and tech innovation.",
                q5_personality="Friends describe me as empathetic, organized, optimistic, and articulate.",
                q6_dealbreakers="Smoking, substance abuse, and dishonesty are total non-starters.",
            )
            .build()
        )

        user = UserSimulator(custom_persona)

        # Validate local profile payload building
        payload = user.profile_payload()
        assert payload["age"] == 27
        assert payload["max_distance_km"] == 25
        assert payload["gender"] == "female"
        assert payload["relationship_goal"] == "long-term"

        async with httpx.AsyncClient(base_url=api_url, timeout=15.0) as client:
            try:
                health = await client.get("/healthz")
                if health.status_code != 200:
                    pytest.skip("Belong API service not available for live simulation.")
            except Exception:
                pytest.skip("Belong API service not running.")

            # Run full flow
            prof_created = await user.create_profile_async(client)
            assert prof_created is True
            onboard_completed = await user.run_onboarding_async(client)
            assert onboard_completed is True
            assert user.status == "completed"
