from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

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
    reasoning: Optional[str] = Field(
        default="",
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
    overall_reasoning: Optional[str] = Field(
        default="",
        description="2-3 sentence executive summary conclusion explaining why these two users match or don't match, highlighting key synergies."
    )
    dimension_results: DimensionResults = Field(
        ...,
        description="Core compatibility dimensions results."
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_dimension_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Normalize 'dimensions' key to 'dimension_results'
            if "dimension_results" not in data and "dimensions" in data:
                data["dimension_results"] = data.pop("dimensions")
            
            # 2. If the LLM returned individual dimensions directly at the root level
            core_dims = ["emotional_needs", "core_values", "lifestyle", "conflict_style"]
            if "dimension_results" not in data:
                root_dims = {k: data.pop(k) for k in core_dims if k in data}
                if root_dims:
                    data["dimension_results"] = root_dims

            # 3. Ensure dimension_results dictionary exists with all 4 required dimensions
            dim_res = data.get("dimension_results")
            if not isinstance(dim_res, dict):
                dim_res = {}

            default_verdict = data.get("overall_verdict", "partial_alignment")
            for dim in core_dims:
                if dim not in dim_res or not isinstance(dim_res[dim], dict):
                    dim_res[dim] = {
                        "verdict": default_verdict,
                        "evidence_a_ids": [],
                        "evidence_b_ids": [],
                        "reasoning": ""
                    }
            data["dimension_results"] = dim_res

            # 4. Ensure overall_verdict is present
            if "overall_verdict" not in data:
                data["overall_verdict"] = "partial_alignment"

        return data
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
