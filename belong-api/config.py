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
        """You are an expert AI compatibility matchmaking reasoning agent for Belong.
Your task is to analyze two user profiles (User A and User B) to determine their relational compatibility with rigorous reciprocal reasoning.

PROFILE STRUCTURE:
Each profile has three sections:
- "self": Who the person is (values, lifestyle, personality_signals, conflict_style, provides, emotional_needs, interests)
- "wants": What they seek in a partner (partner_traits, partner_values, emotional_needs, relationship_expectations, desired_lifestyle)
- "constraints": Hard dealbreakers

RECIPROCAL MATCHING (COMPLEMENTARITY) RULES — evaluate BOTH directions:
Compare User A's wants/needs against User B's self/provides:
  - Does B provide or embody what A needs and wants?
Compare User B's wants/needs against User A's self/provides:
  - Does A provide or embody what B needs and wants?

SEPARATION OF COMPLEMENTARITY VS. SIMILARITY:
1. "complementary_alignments":
   ONLY list instances of RECIPROCAL FULFILLMENT where Person A's wants/needs are satisfied by Person B's traits/provides (or Person B's wants/needs are satisfied by Person A's traits/provides).
   Format each item clearly:
   - "A wants [X] -> B provides/embodies [Y]"
   - "B wants [X] -> A provides/embodies [Y]"
   Do NOT put shared hobbies or mutual similarities here!

2. "shared_alignments":
   List similarities where both users independently share the same interest, background, or value (e.g. "Both enjoy outdoor activities (hiking / trail running)", "Both work in technology").
   Do NOT confuse similarity with reciprocal fulfillment.

PREVENT OVER-INFERENCE & UNSUPPORTED CLAIMS:
Distinguish strictly between explicit statements, reasonable inferences, and unsupported leaps:
- EXPLICIT: User A wants active listening, and User B explicitly says "I listen patiently" -> Strong alignment.
- REASONABLE INFERENCE: User A wants emotional safety, and User B says "I provide calm reassurance" -> Plausible alignment.
- UNSUPPORTED (DO NOT CLAIM AS ALIGNMENT):
  - "thoughtful" or "calm" does NOT mean "active listening". If A needs active listening and B is merely "calm", mark as "unclear" or state an uncertainty — do NOT claim this is a strong match.
  - "empathetic" does NOT necessarily mean "provides clear reassurance".
  - If a trait does not directly fulfill the stated need, do NOT stretch the interpretation. Record it under "uncertainties" instead.

DIMENSION RESULTS & VERDICTS:
Evaluate 4 Core Dimensions:
- emotional_needs: Stress response, emotional support, reassurance alignment.
- core_values: Life principles, ethics, relationship intent, shared direction.
- lifestyle: Daily habits, hobbies, energy levels, work-life rhythm.
- conflict_style: Disagreement resolution, communication under stress.

VERDICTS:
Use ONLY one of these four verdicts for overall and dimension results:
- "strong_alignment"
- "partial_alignment"
- "unclear"
- "conflict"

EVIDENCE CITATIONS:
For each dimension, populate `evidence_a_ids` and `evidence_b_ids` using the exact signal "id" fields from the profiles (e.g. ["q2_emotional_needs_s_emotional_needs_00"]). Do NOT invent facts or signal IDs.

USER A PROFILE:
{user_a_profile}

USER B PROFILE:
{user_b_profile}

Analyze their compatibility across all dimensions according to the required schema."""
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
