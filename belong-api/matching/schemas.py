from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

# --- Categorical Compatibility LLM Output Schemas ---

class DimensionDetail(BaseModel):
    """Specific evidence and verdict for a single compatibility dimension."""
    verdict: str = Field(
        ..., 
        description="Verdict for this dimension: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'"
    )
    evidence_a: Optional[str] = Field(
        default="", 
        description="Direct quote or explicit evidence extracted from User A's profile."
    )
    evidence_b: Optional[str] = Field(
        default="", 
        description="Direct quote or explicit evidence extracted from User B's profile."
    )
    evidence_a_ids: List[str] = Field(
        default_factory=list,
        description="Signal IDs from User A's profile supporting this verdict."
    )
    evidence_b_ids: List[str] = Field(
        default_factory=list,
        description="Signal IDs from User B's profile supporting this verdict."
    )
    reasoning: Optional[str] = Field(
        default="",
        description="Explanation of the verdict based on cited evidence."
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
        description="2-3 sentence executive summary conclusion explaining why these two users match or don't match."
    )
    dimension_results: DimensionResults

    @model_validator(mode="before")
    @classmethod
    def normalize_dimension_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "dimension_results" not in data and "dimensions" in data:
                data["dimension_results"] = data.pop("dimensions")
        return data
    complementary_alignments: List[str] = Field(default_factory=list, description="Reciprocal fulfillment alignments")
    shared_alignments: List[str] = Field(default_factory=list, description="Mutual similarity alignments")
    strong_alignments: List[str] = Field(default_factory=list, description="Key areas of mutual resonance")
    potential_conflicts: List[str] = Field(default_factory=list, description="Areas of friction or misalignment")
    dealbreaker_violations: List[str] = Field(default_factory=list, description="Hard constraints or dealbreakers triggered")
    uncertainties: List[str] = Field(default_factory=list, description="Areas where info was insufficient to evaluate")

# --- HTTP API Request / Response Schemas ---

class JobCreateResponse(BaseModel):
    """Response returned upon enqueuing an async job (HTTP 202 Accepted)."""
    job_id: UUID
    user_id: UUID
    type: str
    status: str
    created_at: datetime

class JobStatusResponse(BaseModel):
    """Response returned when polling job status."""
    job_id: UUID
    user_id: UUID
    type: str
    status: str  # pending, running, completed, failed, cancelled
    attempts: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

class MatchCandidateResponse(BaseModel):
    """Detailed qualitative compatibility breakdown for a single matched candidate."""
    id: Optional[UUID] = Field(None, description="Unique compatibility result record ID")
    match_id: Optional[UUID] = Field(None, description="Matching job run ID that generated this evaluation")
    user_a_id: Optional[UUID] = Field(None, description="UUID of the target user receiving the analysis")
    user_b_id: UUID = Field(..., description="UUID of the matched candidate user")
    user_b_name: Optional[str] = Field(None, description="Name or handle of the candidate user")
    overall_verdict: str = Field(..., description="Overall verdict: 'strong_alignment', 'partial_alignment', 'unclear', or 'conflict'")
    overall_reasoning: Optional[str] = Field("", description="Executive summary conclusion addressed directly to the user ('You').")
    dimension_results: Dict[str, Any] = Field(default_factory=dict, description="Detailed evaluations per dimension with evidence citations.")
    strong_alignments: List[str] = Field(default_factory=list, description="All positive alignment highlights")
    complementary_alignments: List[str] = Field(default_factory=list, description="Reciprocal fulfillment alignments (what You seek -> candidate provides)")
    shared_alignments: List[str] = Field(default_factory=list, description="Mutual similarity alignments (shared values, habits, interests)")
    potential_conflicts: List[str] = Field(default_factory=list, description="Areas of friction or misalignment")
    dealbreaker_violations: List[str] = Field(default_factory=list, description="Hard constraints or dealbreakers triggered")
    uncertainties: List[str] = Field(default_factory=list, description="Areas where info was ambiguous or insufficient")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MatchesListResponse(BaseModel):
    """Response containing list of compatibility matches for a user."""
    user_id: UUID = Field(..., description="Target user ID")
    total_matches: int = Field(..., description="Count of matched candidates")
    matches: List[MatchCandidateResponse] = Field(..., description="List of match candidate details")
