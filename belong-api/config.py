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
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")  # LLM backend: groq, google, openai, anthropic
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")  # Model used for extraction & reasoning
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))  # Creativity vs determinism
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)  # Groq API key
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")  # Sentence transformer model for vector embeddings
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))  # Vector dimension (must match model output)
    USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"  # Use local sentence-transformers lib instead of HF API
    HF_API_TOKEN: Optional[str] = os.getenv("HF_API_TOKEN", None)  # Hugging Face Inference API token (required if USE_LOCAL_EMBEDDINGS=false)

    # --- Configurable Prompt Templates ---
    PAIRWISE_REASONING_PROMPT_TEMPLATE: str = os.getenv(
        "PAIRWISE_REASONING_PROMPT_TEMPLATE",
        """You are an expert AI compatibility matchmaking reasoning agent.
Your task is to analyze two user profiles (User A and User B) to determine their relational compatibility.

PROFILE STRUCTURE:
Each profile has three sections:
- "self": Who the person is (values, lifestyle, personality, conflict_style, provides, emotional_needs, interests)
- "wants": What they seek in a partner (partner_traits, partner_values, emotional_needs, relationship_expectations, desired_lifestyle)
- "constraints": Hard dealbreakers

RECIPROCAL MATCHING RULES — evaluate BOTH directions for each dimension:

  EMOTIONAL NEEDS:
    A.wants.emotional_needs  ↔  B.self.provides   (Does B provide what A needs?)
    B.wants.emotional_needs  ↔  A.self.provides   (Does A provide what B needs?)

  VALUES:
    A.wants.partner_values   ↔  B.self.values     (Does B hold the values A wants?)
    B.wants.partner_values   ↔  A.self.values     (Does A hold the values B wants?)

  LIFESTYLE:
    A.wants.desired_lifestyle ↔  B.self.lifestyle  (Does B's life match what A wants?)
    B.wants.desired_lifestyle ↔  A.self.lifestyle  (Does A's life match what B wants?)

  RELATIONSHIP EXPECTATIONS:
    A.wants.relationship_expectations ↔ B.self.provides + B.self.values
    B.wants.relationship_expectations ↔ A.self.provides + A.self.values

  CONFLICT:
    A.wants (partner conflict style) ↔ B.self.conflict_style
    B.wants (partner conflict style) ↔ A.self.conflict_style

STRICT RULES:
1. NEVER compare A.wants against B.wants as evidence of reciprocal compatibility.
   Shared wants are SIMILARITY, not COMPLEMENTARITY. Report them separately.
2. Anti-Hallucination: Cite ONLY evidence that exists in the profile signals.
   You MUST reference specific signal IDs (field "id" in each signal item).
   Do NOT invent new facts about a user that aren't in their extracted signals.
   Example of forbidden reasoning: "Bob's trail running may be solo-oriented" — this is not in his profile.
3. Categorical Verdicts: Use ONLY one of these four verdicts:
   - "strong_alignment"
   - "partial_alignment"
   - "unclear"
   - "conflict"

SIMILARITY vs. COMPLEMENTARITY:
- Complementarity: A needs X and B provides X (or vice versa). This is the core product thesis.
- Similarity: Both A and B independently want or have the same thing. This is a bonus but not the primary signal.
Report these separately in the output.

USER A PROFILE:
{user_a_profile}

USER B PROFILE:
{user_b_profile}

Analyze their compatibility. For each dimension verdict, populate evidence_a_ids and evidence_b_ids with the signal IDs from the profiles above. Do NOT write free-text evidence strings — reference IDs only."""
    )

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
            targets=["wants.relationship_expectations", "wants.partner_traits", "wants.partner_values"],
            description="Extract relationship goals, commitment style, and desired qualities/values in a partner."
        ),
        QuestionConfig(
            id="q2_emotional_needs",
            topic="Emotional Needs",
            prompt="When things get stressful or difficult, what do you need from a partner, and what helps you feel supported?",
            targets=["self.emotional_needs", "wants.partner_traits"],
            description="Extract emotional support style, stress response expectations, and vulnerability needs."
        ),
        QuestionConfig(
            id="q3_conflict_provides",
            topic="Conflict Style & What You Provide",
            prompt="When there's a disagreement, how do you usually handle it? And what do you feel you bring to a relationship as a partner?",
            targets=["self.conflict_style", "self.provides"],
            description="Extract conflict resolution approach, communication tendencies, and personal contributions."
        ),
        QuestionConfig(
            id="q4_lifestyle_values",
            topic="Lifestyle, Values, Interests & Goals",
            prompt="What does your day-to-day life look like, what do you enjoy doing, and what values or future goals are important to you?",
            targets=["self.lifestyle", "self.interests", "self.values", "self.life_goals", "wants.desired_lifestyle"],
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
            prompt="What are non-negotiable dealbreakers or absolute hard constraints for you in a partner or relationship?",
            targets=["constraints.dealbreakers", "wants.partner_values"],
            description="Extract non-negotiables, dealbreakers, and absolute boundaries."
        )
    ]

settings = Settings()
