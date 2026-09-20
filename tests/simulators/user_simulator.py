"""
User Simulator & Configurable Persona Builder
==============================================
Provides reusable actors to simulate real human users performing onboarding,
trait extraction, profile creation, and matching operations.

Supports:
- Standard personas loaded from personas.json
- Fully configurable dynamic personas created programmatically via PersonaConfig.builder()
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4, UUID
import httpx


class PersonaConfig:
    """Configurable definition of a synthetic user persona."""

    def __init__(
        self,
        id: str,
        category: str = "custom",
        demographics: Optional[Dict[str, Any]] = None,
        question_responses: Optional[Dict[str, str]] = None,
        profile: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.category = category
        self.demographics = demographics or {
            "age": 28,
            "gender": "other",
            "orientation": "straight",
            "relationship_goal": "long-term",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "preferred_age_min": 21,
            "preferred_age_max": 35,
            "preferred_genders": ["female", "male"],
            "max_distance_km": 50,
            "required_relationship_goal": "long-term",
        }
        self.question_responses = question_responses or {
            "q1_intent_partner": "Looking for a committed, communicative, long-term partner.",
            "q2_emotional_needs": "I value calm reassurance, active listening, and open vulnerability.",
            "q3_conflict_provides": "I handle disagreements calmly through collaborative dialogue.",
            "q4_lifestyle_values": "Active, healthy lifestyle, continuous learning, and outdoor activities.",
            "q5_personality": "Empathetic, warm, grounded, and dependable.",
            "q6_dealbreakers": "Dishonesty and disrespect are non-negotiable dealbreakers.",
        }
        self.profile = profile or {}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaConfig":
        """Instantiates a PersonaConfig from a dictionary (e.g. from personas.json)."""
        return cls(
            id=data.get("id", str(uuid4())),
            category=data.get("category", "custom"),
            demographics=data.get("demographics"),
            question_responses=data.get("question_responses"),
            profile=data.get("profile"),
        )

    @classmethod
    def builder(cls, persona_id: str) -> "PersonaBuilder":
        """Returns a fluid builder instance for creating a custom persona."""
        return PersonaBuilder(persona_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PersonaConfig back into a dictionary."""
        return {
            "id": self.id,
            "category": self.category,
            "demographics": self.demographics,
            "question_responses": self.question_responses,
            "profile": self.profile,
        }


class PersonaBuilder:
    """Fluid builder for configuring dynamic test personas."""

    def __init__(self, persona_id: str):
        self._id = persona_id
        self._category = "custom"
        self._demographics: Dict[str, Any] = {
            "age": 28,
            "gender": "other",
            "orientation": "straight",
            "relationship_goal": "long-term",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "preferred_age_min": 21,
            "preferred_age_max": 35,
            "preferred_genders": ["male", "female"],
            "max_distance_km": 50,
            "required_relationship_goal": "long-term",
        }
        self._responses: Dict[str, str] = {}
        self._profile: Dict[str, Any] = {}

    def with_category(self, category: str) -> "PersonaBuilder":
        self._category = category
        return self

    def with_age(self, age: int, preferred_min: int = 21, preferred_max: int = 35) -> "PersonaBuilder":
        self._demographics["age"] = age
        self._demographics["preferred_age_min"] = preferred_min
        self._demographics["preferred_age_max"] = preferred_max
        return self

    def with_gender(self, gender: str, preferred_genders: Optional[List[str]] = None) -> "PersonaBuilder":
        self._demographics["gender"] = gender
        if preferred_genders is not None:
            self._demographics["preferred_genders"] = preferred_genders
        return self

    def with_location(self, latitude: float, longitude: float, max_distance_km: int = 50) -> "PersonaBuilder":
        self._demographics["latitude"] = latitude
        self._demographics["longitude"] = longitude
        self._demographics["max_distance_km"] = max_distance_km
        return self

    def with_relationship_goal(self, goal: str, required_goal: Optional[str] = None) -> "PersonaBuilder":
        self._demographics["relationship_goal"] = goal
        self._demographics["required_relationship_goal"] = required_goal
        return self

    def with_responses(self, **responses) -> "PersonaBuilder":
        """
        Pass responses by question key, e.g.:
        with_responses(
            q1_intent_partner="...",
            q2_emotional_needs="...",
            q3_conflict_provides="...",
            q4_lifestyle_values="...",
            q5_personality="...",
            q6_dealbreakers="..."
        )
        """
        self._responses.update(responses)
        return self

    def with_dealbreaker(self, dealbreaker_text: str) -> "PersonaBuilder":
        self._responses["q6_dealbreakers"] = dealbreaker_text
        return self

    def build(self) -> PersonaConfig:
        default_responses = {
            "q1_intent_partner": "Looking for a committed partner.",
            "q2_emotional_needs": "I value calm reassurance.",
            "q3_conflict_provides": "I handle disagreements calmly.",
            "q4_lifestyle_values": "Active, healthy lifestyle.",
            "q5_personality": "Warm and dependable.",
            "q6_dealbreakers": "Dishonesty and disrespect.",
        }
        merged_responses = {**default_responses, **self._responses}
        return PersonaConfig(
            id=self._id,
            category=self._category,
            demographics=self._demographics,
            question_responses=merged_responses,
            profile=self._profile,
        )


class UserSimulator:
    """Actor simulating a human user's actions during onboarding & matching."""

    def __init__(self, persona: PersonaConfig, user_id: Optional[str] = None):
        self.persona = persona
        self.user_id: str = user_id or str(uuid4())
        self.conversation_id: Optional[str] = None
        self.status: str = "initialized"
        self.extracted_profile: Optional[Dict[str, Any]] = None

    def profile_payload(self) -> Dict[str, Any]:
        """Constructs API payload for POST /profiles."""
        demo = self.persona.demographics
        return {
            "user_id": self.user_id,
            "age": demo.get("age", 25),
            "gender": demo.get("gender", "other"),
            "orientation": demo.get("orientation", "straight"),
            "relationship_goal": demo.get("relationship_goal", "long-term"),
            "latitude": demo.get("latitude", 37.7749),
            "longitude": demo.get("longitude", -122.4194),
            "preferred_age_min": demo.get("preferred_age_min", 21),
            "preferred_age_max": demo.get("preferred_age_max", 35),
            "max_distance_km": demo.get("max_distance_km", 50),
            "preferred_genders": demo.get("preferred_genders", []),
            "required_relationship_goal": demo.get("required_relationship_goal"),
            "profile": self.persona.profile,
        }

    async def _post_with_fallback(self, client: httpx.AsyncClient, path: str, **kwargs) -> httpx.Response:
        """Helper to try route both directly and with /api prefix if 404 is encountered."""
        res = await client.post(path, **kwargs)
        if res.status_code == 404 and not path.startswith("/api"):
            alt_path = f"/api{path}"
            res = await client.post(alt_path, **kwargs)
        return res

    async def _get_with_fallback(self, client: httpx.AsyncClient, path: str, **kwargs) -> httpx.Response:
        """Helper to try GET route both directly and with /api prefix if 404 is encountered."""
        res = await client.get(path, **kwargs)
        if res.status_code == 404 and not path.startswith("/api"):
            alt_path = f"/api{path}"
            res = await client.get(alt_path, **kwargs)
        return res

    async def create_profile_async(self, client: httpx.AsyncClient) -> bool:
        """Registers the user profile via API."""
        payload = self.profile_payload()
        res = await self._post_with_fallback(client, "/profiles", json=payload)
        if res.status_code in (200, 201):
            self.status = "profile_created"
            return True
        return False

    async def run_onboarding_async(self, client: httpx.AsyncClient) -> bool:
        """Simulates multi-turn interactive conversational onboarding."""
        start_res = await self._post_with_fallback(client, "/onboarding/session", json={"user_id": self.user_id})
        if start_res.status_code != 201:
            return False

        session_data = start_res.json()
        self.conversation_id = session_data["conversation_id"]

        q_keys = [
            "q1_intent_partner",
            "q2_emotional_needs",
            "q3_conflict_provides",
            "q4_lifestyle_values",
            "q5_personality",
            "q6_dealbreakers",
        ]

        conv_status = "active"
        for q_key in q_keys:
            if conv_status == "completed":
                break

            user_msg = self.persona.question_responses.get(
                q_key, "I value honest communication and balance."
            )
            msg_res = await self._post_with_fallback(
                client,
                "/onboarding/message",
                json={
                    "conversation_id": self.conversation_id,
                    "message": user_msg,
                },
            )

            if msg_res.status_code != 200:
                return False

            reply_data = msg_res.json()
            conv_status = reply_data.get("status", "active")

        self.status = conv_status
        return conv_status == "completed"

    async def trigger_embeddings_async(self, client: httpx.AsyncClient) -> bool:
        """Triggers embedding extraction job."""
        res = await self._post_with_fallback(client, f"/profiles/{self.user_id}/embeddings")
        if res.status_code in (200, 202):
            self.status = "embeddings_triggered"
            return True
        return False

    async def request_matches_async(self, client: httpx.AsyncClient) -> Optional[str]:
        """Triggers matching calculation for user."""
        res = await self._post_with_fallback(client, "/matches", headers={"X-User-ID": self.user_id})
        if res.status_code in (200, 202):
            data = res.json()
            return data.get("job_id")
        return None


    def evaluate_match_outcome(
        self,
        other_user: "UserSimulator",
        match_result: Optional[Dict[str, Any]],
        expected_spec: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluates whether the generated match result between self and other_user
        satisfies expected invariant rules.
        """
        evaluation = {
            "pair": f"{self.persona.id} -> {other_user.persona.id}",
            "passed": True,
            "reasons": [],
        }

        if not expected_spec:
            return evaluation

        # Geographic distance exclusion check
        if expected_spec.get("expected_in_recall") is False:
            if match_result is not None and match_result.get("score", 0) > 0:
                evaluation["passed"] = False
                evaluation["reasons"].append(
                    f"Expected exclusion (e.g. distance), but received match score {match_result.get('score')}"
                )
            return evaluation

        # Expect in recall check
        if expected_spec.get("expected_in_recall") is True:
            if not match_result:
                evaluation["passed"] = False
                evaluation["reasons"].append(
                    f"Expected {other_user.persona.id} in recall, but no match was found."
                )
                return evaluation

            # Verdict check
            allowed_verdicts = expected_spec.get("allowed_verdicts", [])
            actual_verdict = match_result.get("verdict")
            if allowed_verdicts and actual_verdict not in allowed_verdicts:
                evaluation["passed"] = False
                evaluation["reasons"].append(
                    f"Verdict '{actual_verdict}' not in allowed verdicts {allowed_verdicts}"
                )

            # Dealbreaker check
            if expected_spec.get("must_have_dealbreakers") is True:
                dealbreakers = match_result.get("dealbreakers", [])
                if not dealbreakers:
                    evaluation["passed"] = False
                    evaluation["reasons"].append("Expected dealbreakers, but none were returned.")

        return evaluation
