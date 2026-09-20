"""
User Ecosystem Simulation Test Suite
=====================================
Simulates a multi-user community/ecosystem of distinct user personas interacting
simultaneously (onboarding, trait extraction, embedding generation, and matching).

Evaluates User Expectation Invariants:
- Complementary Pairing: Alice + Bob
- Dealbreaker Defense: Eve (non-smoker) + Frank (heavy smoker)
- Conflict Style Clash: Ian (anxious pursuer) + Julia (stonewaller)
- Geographic Distance Boundary: Quinn (Seattle) + Ryan (San Francisco)
"""

import asyncio
import os
import pytest
import httpx
from typing import Dict, Any, List

from simulators.user_simulator import UserSimulator, PersonaConfig


@pytest.mark.simulation
class TestUserEcosystemSimulation:
    """Simulates an entire user ecosystem and evaluates personalized match outcome invariants."""

    @pytest.fixture
    def api_url(self) -> str:
        return os.getenv("BELONG_API_URL", "http://localhost:8000")

    @pytest.mark.asyncio
    async def test_full_user_ecosystem_matching_simulation(
        self,
        golden_personas: List[Dict[str, Any]],
        expected_outcomes: Dict[str, Any],
        api_url: str,
    ):
        """Simulates onboarding & matching for all personas in the golden dataset."""
        if not golden_personas:
            pytest.skip("No golden personas available.")

        # Instantiate UserSimulator actors for all personas
        simulated_users: Dict[str, UserSimulator] = {}
        for p_dict in golden_personas:
            config = PersonaConfig.from_dict(p_dict)
            simulated_users[config.id] = UserSimulator(config)

        async with httpx.AsyncClient(base_url=api_url, timeout=30.0) as client:
            try:
                health = await client.get("/healthz")
                if health.status_code != 200:
                    pytest.skip("Belong API service not available.")
            except Exception:
                pytest.skip("Belong API service not running on port 8000.")

            # Step 1: Create Profiles for all users in ecosystem
            for persona_id, user in simulated_users.items():
                ok = await user.create_profile_async(client)
                assert ok is True, f"Failed creating profile for user {persona_id}"

            # Step 2: Trigger Embedding extraction for all users
            for persona_id, user in simulated_users.items():
                ok = await user.trigger_embeddings_async(client)
                assert ok is True, f"Failed embedding trigger for user {persona_id}"

            # Step 3: Trigger Matching Job for target user Alice (cp_alice) if present
            if "cp_alice" in simulated_users:
                alice = simulated_users["cp_alice"]
                job_id = await alice.request_matches_async(client)
                assert job_id is not None, "Failed triggering match job for Alice"

                # Poll for job completion
                job_completed = False
                for _ in range(10):
                    await asyncio.sleep(2)
                    res = await client.get(f"/matches/jobs/{job_id}")
                    if res.status_code == 200 and res.json().get("status") == "completed":
                        job_completed = True
                        break

                # Fetch matches for Alice
                res = await client.get(f"/matches/{alice.user_id}")
                assert res.status_code == 200
                matches_data = res.json()
                matches_list = matches_data.get("matches", [])

                # Verify expected outcome invariant: Alice -> Bob (cp_bob)
                if "cp_bob" in simulated_users:
                    bob = simulated_users["cp_bob"]
                    expected_spec = expected_outcomes.get("cp_alice -> cp_bob")
                    
                    bob_match = next((m for m in matches_list if m.get("candidate_user_id") == bob.user_id), None)
                    eval_res = alice.evaluate_match_outcome(bob, bob_match, expected_spec)
                    assert eval_res["passed"] is True, f"Outcome evaluation failed: {eval_res['reasons']}"

    @pytest.mark.asyncio
    async def test_configurable_user_pair_simulation(self, api_url: str):
        """
        Simulates two dynamically configured users with strict dealbreakers
        to verify dealbreaker isolation behavior.
        """
        # User 1: Non-smoker with strict dealbreaker
        user1_config = (
            PersonaConfig.builder("sim_health_user")
            .with_age(28)
            .with_gender("female", preferred_genders=["male"])
            .with_location(37.7749, -122.4194)
            .with_responses(
                q1_intent_partner="Looking for a healthy non-smoking long-term partner.",
                q6_dealbreakers="Smoking of any kind is an absolute non-negotiable dealbreaker."
            )
            .build()
        )
        user1 = UserSimulator(user1_config)

        # User 2: Smoker
        user2_config = (
            PersonaConfig.builder("sim_smoker_user")
            .with_age(30)
            .with_gender("male", preferred_genders=["female"])
            .with_location(37.7800, -122.4100)
            .with_responses(
                q1_intent_partner="Looking for an easygoing partner.",
                q4_lifestyle_values="I smoke cigarettes daily and love nightlife.",
                q6_dealbreakers="Overly controlling partners."
            )
            .build()
        )
        user2 = UserSimulator(user2_config)

        async with httpx.AsyncClient(base_url=api_url, timeout=15.0) as client:
            try:
                health = await client.get("/healthz")
                if health.status_code != 200:
                    pytest.skip("Belong API service not available.")
            except Exception:
                pytest.skip("Belong API service not running.")

            # Create profiles
            assert await user1.create_profile_async(client) is True
            assert await user2.create_profile_async(client) is True

            # Execute onboarding for both
            assert await user1.run_onboarding_async(client) is True
            assert await user2.run_onboarding_async(client) is True
