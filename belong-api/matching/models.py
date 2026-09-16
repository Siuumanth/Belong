from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class CandidateMatch(BaseModel):
    """Represents a retrieved candidate from Stage 1 retrieval."""
    user_id: UUID
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
