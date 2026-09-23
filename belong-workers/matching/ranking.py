import logging
from typing import List, Dict, Any, Tuple
from matching.schemas import PairwiseCompatibilityOutput

logger = logging.getLogger(__name__)

VERDICT_RANK = {
    "strong_alignment": 4,
    "partial_alignment": 3,
    "unclear": 2,
    "conflict": 1
}

def calculate_rank_key(
    output: PairwiseCompatibilityOutput, 
    stage1_combined_score: float = 0.0
) -> Tuple[int, int, int, float]:
    """Calculates a deterministic sort key tuple for ranking candidate compatibility.

    Sort Order (Descending):
    1. Dealbreaker violations (0 is better than >0) -> represented by -len(dealbreaker_violations)
    2. Overall verdict score (strong_alignment=4, partial_alignment=3, unclear=2, conflict=1)
    3. Net balance: len(strong_alignments) - len(potential_conflicts)
    4. Stage 1 vector combined score tie-breaker
    """
    dealbreaker_penalty = -len(output.dealbreaker_violations)
    verdict_score = VERDICT_RANK.get(output.overall_verdict, 1)
    # Schema uses complementary_alignments + shared_alignments instead of strong_alignments
    total_alignments = len(output.complementary_alignments) + len(output.shared_alignments)
    net_alignment = total_alignments - len(output.potential_conflicts)

    return (dealbreaker_penalty, verdict_score, net_alignment, stage1_combined_score)

def rank_candidates(
    evaluated_candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Sorts a list of evaluated candidate dictionaries in descending order of compatibility."""
    for cand in evaluated_candidates:
        output: PairwiseCompatibilityOutput = cand["compatibility_output"]
        stage1_score = cand.get("stage1_combined_score", 0.0)
        cand["_sort_key"] = calculate_rank_key(output, stage1_score)

    sorted_candidates = sorted(
        evaluated_candidates,
        key=lambda c: c["_sort_key"],
        reverse=True
    )

    # Clean up internal sort key
    for cand in sorted_candidates:
        cand.pop("_sort_key", None)

    return sorted_candidates
