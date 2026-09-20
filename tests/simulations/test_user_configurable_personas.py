"""
Configurable User Personas Test Suite
======================================
Tests the programmatically configurable user persona framework (PersonaConfig & PersonaBuilder).

Ensures users can be fully customized with:
- Custom demographics (age, gender, orientation, location, distance limit)
- Custom question responses (q1-q6)
- Custom dealbreakers and relationship goals
- Custom extracted profile traits
"""

import pytest
from typing import Dict, Any

from simulators.user_simulator import UserSimulator, PersonaConfig, PersonaBuilder


@pytest.mark.simulation
class TestConfigurableUserPersonas:
    """Tests configurable persona creation and customization capabilities."""

    def test_default_persona_config_defaults(self):
        """Verifies default fallback values for PersonaConfig."""
        persona = PersonaConfig("default_user_1")
        assert persona.id == "default_user_1"
        assert persona.category == "custom"
        assert persona.demographics["age"] == 28
        assert persona.demographics["latitude"] == 37.7749
        assert "q1_intent_partner" in persona.question_responses

    def test_persona_builder_fluid_configuration(self):
        """Verifies fluid builder methods for customizing user personas."""
        persona = (
            PersonaConfig.builder("custom_user_alpha")
            .with_category("custom_test")
            .with_age(32, preferred_min=28, preferred_max=40)
            .with_gender("male", preferred_genders=["female"])
            .with_location(40.7128, -74.0060, max_distance_km=30)  # NYC coordinates
            .with_relationship_goal("marriage", required_goal="marriage")
            .with_responses(
                q1_intent_partner="Seeking a loving partner for marriage and family in NYC.",
                q2_emotional_needs="Open communication, emotional security, and shared goals.",
                q3_conflict_provides="Calm discussion, active listening, and practical solutions.",
                q4_lifestyle_values="Architecture, museums, fitness, and family dinners.",
                q5_personality="Grounded, organized, warm, and loyal.",
                q6_dealbreakers="Dishonesty and smoking are absolute dealbreakers.",
            )
            .build()
        )

        assert persona.id == "custom_user_alpha"
        assert persona.category == "custom_test"
        assert persona.demographics["age"] == 32
        assert persona.demographics["preferred_age_min"] == 28
        assert persona.demographics["preferred_age_max"] == 40
        assert persona.demographics["gender"] == "male"
        assert persona.demographics["preferred_genders"] == ["female"]
        assert persona.demographics["latitude"] == 40.7128
        assert persona.demographics["longitude"] == -74.0060
        assert persona.demographics["max_distance_km"] == 30
        assert persona.demographics["relationship_goal"] == "marriage"
        assert persona.demographics["required_relationship_goal"] == "marriage"
        assert "NYC" in persona.question_responses["q1_intent_partner"]

    def test_user_simulator_payload_generation(self):
        """Verifies that UserSimulator generates exact API payloads matching persona configuration."""
        persona = (
            PersonaConfig.builder("config_user_beta")
            .with_age(26)
            .with_gender("female", preferred_genders=["male"])
            .with_location(34.0522, -118.2437, max_distance_km=40)  # LA coordinates
            .with_dealbreaker("Non-smoker only.")
            .build()
        )

        user = UserSimulator(persona)
        payload = user.profile_payload()

        assert payload["user_id"] == user.user_id
        assert payload["age"] == 26
        assert payload["gender"] == "female"
        assert payload["latitude"] == 34.0522
        assert payload["longitude"] == -118.2437
        assert payload["max_distance_km"] == 40
        assert persona.question_responses["q6_dealbreakers"] == "Non-smoker only."

    def test_batch_configurable_user_population_creation(self):
        """Verifies programmatic creation of a population of customized simulated users."""
        population_configs = [
            PersonaConfig.builder(f"user_{i}")
            .with_age(20 + i * 2)
            .with_location(37.7749 + i * 0.01, -122.4194 + i * 0.01)
            .build()
            for i in range(5)
        ]

        simulated_users = [UserSimulator(config) for config in population_configs]

        assert len(simulated_users) == 5
        for i, user in enumerate(simulated_users):
            assert user.persona.demographics["age"] == 20 + i * 2
            assert user.status == "initialized"
