import unittest
from uuid import uuid4
from matching.schemas import (
    PairwiseCompatibilityOutput,
    DimensionResults,
    DimensionDetail
)
from matching.ranking import calculate_rank_key, rank_candidates
from matching.compatibility import validation_node, PairwiseState
from embeddings.serializer import CanonicalSerializer

class TestLayer1UnitMatching(unittest.TestCase):
    def setUp(self):
        self.sample_dim_detail = DimensionDetail(
            verdict="strong_alignment",
            evidence_a="I value honesty",
            evidence_b="Honesty is key"
        )
        self.sample_dim_results = DimensionResults(
            emotional_needs=self.sample_dim_detail,
            core_values=self.sample_dim_detail,
            lifestyle=self.sample_dim_detail,
            conflict_style=self.sample_dim_detail
        )

    def test_calculate_rank_key_precedence(self):
        """Verify sorting precedence: dealbreakers > overall verdict > net alignment balance > vector score."""
        # Strong alignment, no dealbreakers
        out_strong = PairwiseCompatibilityOutput(
            overall_verdict="strong_alignment",
            dimension_results=self.sample_dim_results,
            strong_alignments=["values", "lifestyle"],
            potential_conflicts=[],
            dealbreaker_violations=[],
            uncertainties=[]
        )
        
        # Conflict with 1 dealbreaker
        out_dealbreaker = PairwiseCompatibilityOutput(
            overall_verdict="conflict",
            dimension_results=self.sample_dim_results,
            strong_alignments=["lifestyle"],
            potential_conflicts=["values"],
            dealbreaker_violations=["smoking"],
            uncertainties=[]
        )

        key_strong = calculate_rank_key(out_strong, stage1_combined_score=0.85)
        key_dealbreaker = calculate_rank_key(out_dealbreaker, stage1_combined_score=0.95)

        # No dealbreaker penalty (0) > 1 dealbreaker penalty (-1)
        self.assertGreater(key_strong, key_dealbreaker)

    def test_rank_candidates_sorting_stability(self):
        """Verify candidate list is sorted in descending order of compatibility."""
        cand_a_id = uuid4()
        cand_b_id = uuid4()

        cand_a = {
            "candidate_user_id": cand_a_id,
            "stage1_combined_score": 0.90,
            "compatibility_output": PairwiseCompatibilityOutput(
                overall_verdict="strong_alignment",
                dimension_results=self.sample_dim_results,
                strong_alignments=["values"],
                potential_conflicts=[],
                dealbreaker_violations=[],
                uncertainties=[]
            )
        }
        cand_b = {
            "candidate_user_id": cand_b_id,
            "stage1_combined_score": 0.80,
            "compatibility_output": PairwiseCompatibilityOutput(
                overall_verdict="partial_alignment",
                dimension_results=self.sample_dim_results,
                strong_alignments=["lifestyle"],
                potential_conflicts=[],
                dealbreaker_violations=[],
                uncertainties=[]
            )
        }

        sorted_list = rank_candidates([cand_b, cand_a])
        self.assertEqual(sorted_list[0]["candidate_user_id"], cand_a_id)
        self.assertEqual(sorted_list[1]["candidate_user_id"], cand_b_id)
        # Ensure internal sort key is cleaned up
        self.assertNotIn("_sort_key", sorted_list[0])

    def test_validation_node_verdict_normalization(self):
        """Verify invalid overall verdict is normalized to 'unclear'."""
        invalid_output = PairwiseCompatibilityOutput(
            overall_verdict="super_match_invalid",
            dimension_results=self.sample_dim_results,
            strong_alignments=[],
            potential_conflicts=[],
            dealbreaker_violations=[],
            uncertainties=[]
        )

        state: PairwiseState = {
            "user_a_profile": {},
            "user_b_profile": {},
            "prompt_text": "test",
            "parsed_output": invalid_output,
            "error": None
        }

        res = validation_node(state)
        normalized = res.get("parsed_output")
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.overall_verdict, "unclear")

    def test_canonical_serializer_confidence_filter(self):
        """Verify low-confidence extractions (<0.5) are omitted from canonical embedding text."""
        serializer = CanonicalSerializer(confidence_threshold=0.5)
        profile_data = {
          "self": {
            "values": [
              {"summary": "high confidence honesty", "confidence": 0.9, "evidence": "evidence"},
              {"summary": "low confidence fluff", "confidence": 0.2, "evidence": "fluff"}
            ]
          },
          "wants": {}
        }
        self_text = serializer.serialize_self(profile_data)
        self.assertIn("high confidence honesty", self_text)
        self.assertNotIn("low confidence fluff", self_text)

if __name__ == "__main__":
    unittest.main()
