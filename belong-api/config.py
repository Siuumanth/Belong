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
    # --- External / Environment-Sourced ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # LLM backend: google, openai, anthropic
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")  # Model used for onboarding extraction & reasoning
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))  # Creativity vs determinism (0.0 = strict, 1.0 = creative)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")  # Sentence transformer model for vector embeddings
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))  # Vector dimension (must match model output)
    USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"  # Use local sentence-transformers lib instead of HF API
    HF_API_TOKEN: Optional[str] = os.getenv("HF_API_TOKEN", None)  # Hugging Face Inference API token (required if USE_LOCAL_EMBEDDINGS=false)

    # --- Internal Tuning Constants ---
    # Onboarding
    MAX_FOLLOW_UPS: int = 2  # Max follow-up questions per onboarding topic before moving on

    # Embedding
    EMBEDDING_CONFIDENCE_THRESHOLD: float = 0.5  # Min extraction confidence to include in embedding text (0.0–1.0)

    # Matching & Retrieval
    MATCHING_CANDIDATE_POOL_LIMIT: int = 10  # Max candidates retrieved from pgvector in Stage 1
    MATCHING_PRE_RANK_LIMIT: int = 5  # Top N candidates passed to Stage 2 pairwise LLM reasoning
    MATCHING_MAX_DISTANCE_KM_DEFAULT: int = 100  # Fallback max geographic distance (km) if user hasn't set one
    MATCHING_MIN_SIMILARITY_THRESHOLD: float = 0.0  # Floor combined similarity score; candidates below this are dropped
    MATCHING_BIDIRECTIONAL_WEIGHT: float = 0.5  # Balance: (1-w) * A_wants→B_self + w * B_wants→A_self
    
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
