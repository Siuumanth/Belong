from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    label: str
    summary: str
    quote: str
    question_id: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class SelfProfile(BaseModel):
    values: List[EvidenceItem] = Field(default_factory=list)
    lifestyle: List[EvidenceItem] = Field(default_factory=list)
    personality_signals: List[EvidenceItem] = Field(default_factory=list)
    interests: List[EvidenceItem] = Field(default_factory=list)
    life_goals: List[EvidenceItem] = Field(default_factory=list)
    conflict_style: List[EvidenceItem] = Field(default_factory=list)
    provides: List[EvidenceItem] = Field(default_factory=list)
    emotional_needs: List[EvidenceItem] = Field(default_factory=list)

class WantsProfile(BaseModel):
    partner_traits: List[EvidenceItem] = Field(default_factory=list)
    partner_values: List[EvidenceItem] = Field(default_factory=list)
    relationship_expectations: List[EvidenceItem] = Field(default_factory=list)
    desired_lifestyle: List[EvidenceItem] = Field(default_factory=list)

class ConstraintsProfile(BaseModel):
    dealbreakers: List[EvidenceItem] = Field(default_factory=list)

class StructuredProfileJSON(BaseModel):
    self: SelfProfile = Field(default_factory=SelfProfile)
    wants: WantsProfile = Field(default_factory=WantsProfile)
    constraints: ConstraintsProfile = Field(default_factory=ConstraintsProfile)

class ProfileCreate(BaseModel):
    user_id: UUID
    age: Optional[int] = None
    gender: Optional[str] = None
    orientation: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    relationship_goal: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    max_distance_km: Optional[int] = None
    preferred_genders: List[str] = Field(default_factory=list)
    required_relationship_goal: Optional[str] = None
    profile: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProfileUpdate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    orientation: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    relationship_goal: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    max_distance_km: Optional[int] = None
    preferred_genders: Optional[List[str]] = None
    required_relationship_goal: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None

class ProfileResponse(BaseModel):
    user_id: UUID
    age: Optional[int] = None
    gender: Optional[str] = None
    orientation: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    relationship_goal: Optional[str] = None
    preferred_age_min: Optional[int] = None
    preferred_age_max: Optional[int] = None
    max_distance_km: Optional[int] = None
    preferred_genders: List[str] = Field(default_factory=list)
    required_relationship_goal: Optional[str] = None
    profile: Dict[str, Any] = Field(default_factory=dict)
    extraction_version: str = "v1"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
