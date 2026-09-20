import os
import unittest
import pytest
from typing import Dict, Any

from matching.compatibility import PairwiseCompatibilityAgent
from matching.schemas import PairwiseCompatibilityOutput

@pytest.mark.live
class TestLayer3LLMReasoning(unittest.IsolatedAsyncioTestCase):
    """Layer 3 Live LLM Property & Evidence Grounding Evaluation against Groq API."""

    def setUp(self):
        self.agent = PairwiseCompatibilityAgent()
        self.has_api_key = bool(os.getenv("GROQ_API_KEY"))

    async def test_complementary_pair_properties(self):
        """Verify property-based assertions for complementary pair (Alice & Bob)."""
        if not self.has_api_key:
            self.skipTest("GROQ_API_KEY not set. Skipping live LLM test.")

        user_a = {
            "age": 28, "gender": "female", "relationship_goal": "long-term",
            "self": {
                "values": [{"summary": "honesty and emotional connection", "evidence": "I value honesty, continuous learning, and balance."}],
                "lifestyle": [{"summary": "active and balanced lifestyle", "evidence": "morning yoga, cooking plant-based meals, hiking"}],
                "conflict_style": [{"summary": "calm, communicative resolution", "evidence": "expressing my feelings calmly"}]
            },
            "wants": {
                "partner_traits": [{"summary": "communicative, emotionally available", "evidence": "someone communicative, emotionally available"}],
                "relationship_expectations": [{"summary": "committed long-term partnership", "evidence": "looking for a committed, long-term partner"}]
            }
        }

        user_b = {
            "age": 30, "gender": "male", "relationship_goal": "long-term",
            "self": {
                "values": [{"summary": "integrity and lifelong learning", "evidence": "I value integrity, health, and lifelong learning."}],
                "lifestyle": [{"summary": "active outdoor lifestyle", "evidence": "outdoor activities like trail running and camping"}],
                "conflict_style": [{"summary": "patient listening", "evidence": "I listen carefully, stay patient"}]
            },
            "wants": {
                "partner_traits": [{"summary": "thoughtful, empathetic, active", "evidence": "someone who is thoughtful, empathetic, active"}]
            }
        }

        output: PairwiseCompatibilityOutput = await self.agent.evaluate_pair(user_a, user_b)

        # Property 1: Verdict belongs to positive set
        self.assertIn(output.overall_verdict, ["strong_alignment", "partial_alignment"])
        # Property 2: No dealbreaker violations
        self.assertEqual(len(output.dealbreaker_violations), 0)
        # Property 3: Strong alignments non-empty
        self.assertGreater(len(output.strong_alignments), 0)

        # Property 4: Evidence Grounding Evaluation - check dimension claims reference supported concepts
        dims = output.dimension_results
        for name, dim in [("emotional_needs", dims.emotional_needs), ("core_values", dims.core_values)]:
            self.assertTrue(
                dim.evidence_a != "" and dim.evidence_b != "",
                f"Evidence missing for dimension {name}"
            )

    async def test_semantic_dealbreaker_detection(self):
        """Verify dealbreaker violation (smoking) is caught in Stage 2 for Eve & Frank."""
        if not self.has_api_key:
            self.skipTest("GROQ_API_KEY not set. Skipping live LLM test.")

        user_a = {
            "age": 29, "gender": "female", "relationship_goal": "long-term",
            "self": {"values": [{"summary": "clean living", "evidence": "Clean living, wellness"}]},
            "wants": {"partner_values": [{"summary": "non-smoking non-negotiable dealbreaker", "evidence": "Smoking of any kind is an absolute non-negotiable dealbreaker."}]}
        }

        user_b = {
            "age": 30, "gender": "male", "relationship_goal": "long-term",
            "self": {"lifestyle": [{"summary": "daily tobacco smoker", "evidence": "I smoke cigarettes daily and love nightlife."}]},
            "wants": {"partner_traits": [{"summary": "relaxed", "evidence": "relaxed partner"}]}
        }

        output: PairwiseCompatibilityOutput = await self.agent.evaluate_pair(user_a, user_b)

        # Property 1: Dealbreakers list is non-empty
        self.assertGreater(len(output.dealbreaker_violations), 0)
        # Property 2: Contains reference to smoking
        has_smoke_mention = any("smok" in item.lower() for item in output.dealbreaker_violations)
        self.assertTrue(has_smoke_mention, "Expected dealbreaker output to explicitly mention smoking")

if __name__ == "__main__":
    unittest.main()
