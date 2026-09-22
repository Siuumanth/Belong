from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class CandidateMatch(BaseModel):
    """Represents a retrieved candidate from Stage 1 retrieval."""
    user_id: UUID
    name: Optional[str] = None
    age: Optional[int] = None

    gender: Optional[str] = None
    orientation: Optional[str] = None
    relationship_goal: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    
    # Vector Metrics
    cosine_distance: float
    cosine_similarity: float
    reverse_cosine_distance: Optional[float] = None
    reverse_cosine_similarity: Optional[float] = None
    combined_score: float

class RetrievalOptions(BaseModel):
    """Configurable options for candidate retrieval and pre-ranking."""
    candidate_pool_limit: Optional[int] = None
    pre_rank_limit: Optional[int] = None
    max_distance_km: Optional[int] = None
    min_similarity_threshold: Optional[float] = None
    bidirectional_weight: Optional[float] = None
    require_mutual_age: bool = True
    require_mutual_gender: bool = True
    require_mutual_relationship_goal: bool = True

class DimensionDetail(BaseModel):
    """Specific evidence and verdict for a single compatibility dimension.
    
    Evidence is referenced by signal IDs (the 'id' field on each extracted signal),
    NOT by free-text strings. This prevents the reasoning model from hallucinating
    new facts about a user. The application resolves IDs to actual quotes.
    """
    verdict: str = Field(
        ..., 
        description="Verdict for this dimension: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'"
    )
    evidence_a_ids: List[str] = Field(
        default_factory=list,
        description="Signal IDs from User A's profile that support this verdict (e.g. ['q2_emotional_needs_s_emotional_needs_00'])."
    )
    evidence_b_ids: List[str] = Field(
        default_factory=list,
        description="Signal IDs from User B's profile that support this verdict."
    )
    reasoning: str = Field(
        ...,
        description="1-2 sentence explanation of the verdict based only on the cited signal IDs."
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
    complementary_alignments: List[str] = Field(
        default_factory=list,
        description="Areas where A's needs/wants are met by B's self (and/or vice versa). This is reciprocal fulfillment — the core product signal."
    )
    shared_alignments: List[str] = Field(
        default_factory=list,
        description="Areas where both users independently want or value the same thing (similarity, not complementarity)."
    )
    potential_conflicts: List[str] = Field(default_factory=list, description="Areas of friction or misalignment")
    dealbreaker_violations: List[str] = Field(default_factory=list, description="Hard constraints or dealbreakers triggered")
    uncertainties: List[str] = Field(default_factory=list, description="Areas where info was insufficient to evaluate")
    reciprocity_score: float = Field(
        default=0.0,
        description="0.0–1.0 estimate of how well both partners' needs are mutually fulfilled by the other's self. 1.0 = both directions fully satisfied."
    )
