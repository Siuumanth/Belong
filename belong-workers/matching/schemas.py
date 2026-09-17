from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class DimensionDetail(BaseModel):
    """Specific evidence and verdict for a single compatibility dimension."""
    verdict: str = Field(
        ..., 
        description="Verdict for this dimension: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'"
    )
    evidence_a: str = Field(
        ..., 
        description="Direct quote or explicit evidence extracted from User A's profile."
    )
    evidence_b: str = Field(
        ..., 
        description="Direct quote or explicit evidence extracted from User B's profile."
    )

class DimensionResults(BaseModel):
    """The four core compatibility dimensions evaluated by the reasoning agent."""
    emotional_needs: DimensionDetail
    core_values: DimensionDetail
    lifestyle: DimensionDetail
    conflict_style: DimensionDetail

class PairwiseCompatibilityOutput(BaseModel):
    """Qualitative structured output produced by the LangGraph pairwise compatibility reasoning agent."""
    overall_verdict: str = Field(
        ..., 
        description="Overall verdict: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'"
    )
    dimension_results: DimensionResults
    strong_alignments: List[str] = Field(default_factory=list, description="Key areas of mutual resonance")
    potential_conflicts: List[str] = Field(default_factory=list, description="Areas of friction or misalignment")
    dealbreaker_violations: List[str] = Field(default_factory=list, description="Hard constraints or dealbreakers triggered")
    uncertainties: List[str] = Field(default_factory=list, description="Areas where info was insufficient to evaluate")
