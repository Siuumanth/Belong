from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

# --- Categorical Compatibility LLM Output Schemas ---

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
    user_b_id: UUID
    overall_verdict: str
    dimension_results: Dict[str, Any]
    strong_alignments: List[str]
    complementary_alignments: List[str] = Field(default_factory=list)
    shared_alignments: List[str] = Field(default_factory=list)
    potential_conflicts: List[str]
    dealbreaker_violations: List[str]
    uncertainties: List[str]

class MatchesListResponse(BaseModel):
    """Response containing list of compatibility matches for a user."""
    user_id: UUID
    total_matches: int
    matches: List[MatchCandidateResponse]
