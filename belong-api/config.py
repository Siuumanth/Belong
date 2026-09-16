import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class QuestionConfig(BaseModel):
    id: str
    topic: str
    prompt: str
    targets: List[str]
    description: str

class Settings(BaseModel):
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # google, openai, anthropic
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # Onboarding limits
    MAX_FOLLOW_UPS: int = int(os.getenv("MAX_FOLLOW_UPS", "2"))
    
    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    EMBEDDING_CONFIDENCE_THRESHOLD: float = float(os.getenv("EMBEDDING_CONFIDENCE_THRESHOLD", "0.5"))
    USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"
    HF_API_TOKEN: Optional[str] = os.getenv("HF_API_TOKEN", None)

    # Matching & Retrieval Settings
    MATCHING_CANDIDATE_POOL_LIMIT: int = int(os.getenv("MATCHING_CANDIDATE_POOL_LIMIT", "50"))
    MATCHING_PRE_RANK_LIMIT: int = int(os.getenv("MATCHING_PRE_RANK_LIMIT", "15"))
    MATCHING_MAX_DISTANCE_KM_DEFAULT: int = int(os.getenv("MATCHING_MAX_DISTANCE_KM_DEFAULT", "100"))
    MATCHING_MIN_SIMILARITY_THRESHOLD: float = float(os.getenv("MATCHING_MIN_SIMILARITY_THRESHOLD", "0.0"))
    MATCHING_BIDIRECTIONAL_WEIGHT: float = float(os.getenv("MATCHING_BIDIRECTIONAL_WEIGHT", "0.5"))  # 0.5 * (A_wants_B_self) + 0.5 * (B_wants_A_self)
    
    # Questions Configuration
    ONBOARDING_QUESTIONS: List[QuestionConfig] = [
        QuestionConfig(
            id="q1_intent_partner",
            topic="Relationship Intent & Partner Traits",
            prompt="What are you looking for in a relationship, and what kind of person tends to be a good fit for you?",
            targets=["wants.relationship_expectations", "wants.partner_traits"],
            description="Extract relationship goals, commitment style, and desired qualities in a partner."
        ),
        QuestionConfig(
            id="q2_emotional_needs",
            topic="Emotional Needs",
            prompt="What do you most need from a partner when things get stressful or difficult?",
            targets=["self.emotional_needs", "wants.partner_traits"],
            description="Extract emotional support style, stress response expectations, and vulnerability needs."
        ),
        QuestionConfig(
            id="q3_conflict_provides",
            topic="Conflict Style & What You Provide",
            prompt="How do you naturally handle disagreements, differences and what do you bring to a relationship?",
            targets=["self.conflict_style", "self.provides"],
            description="Extract conflict resolution approach, communication tendencies, and personal contributions."
        ),
        QuestionConfig(
            id="q4_lifestyle_values",
            topic="Lifestyle, Values, Interests & Goals",
            prompt="What does your day-to-day life look like, what do you enjoy, and what kind of life are you building for yourself?",
            targets=["self.lifestyle", "self.values", "self.interests", "wants.desired_lifestyle"],
            description="Extract daily habits, core principles, hobbies/passions, and future life aspirations."
        ),
        QuestionConfig(
            id="q5_personality",
            topic="Self-Description & Personality",
            prompt="How would people close to you describe you, and what do you think makes you a good partner?",
            targets=["self.personality_signals", "self.provides"],
            description="Extract peer-perceived traits, self-awareness, and relational strengths."
        ),
        QuestionConfig(
            id="q6_dealbreakers",
            topic="Dealbreakers & Hard Constraints",
            prompt="What are things that are absolute dealbreakers for you?",
            targets=["constraints.dealbreakers", "wants.partner_values"],
            description="Extract non-negotiables, dealbreakers, and absolute boundaries."
        )
    ]

settings = Settings()
