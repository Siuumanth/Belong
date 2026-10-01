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
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")  # Model used for extraction & reasoning
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
Your task is to analyze complete user evidence packages (User A and User B) to determine their relational compatibility using evidence-grounded, open-ended reasoning.

INPUT EVIDENCE STRUCTURE:
Each user profile includes:
- Structured signals (`self`, `wants`, `constraints`)
- `other_signals`: Emergent or unmapped signals that don't fit standard dimensions
- `original_responses`: The user's raw onboarding answers preserving exact nuance and context

REASONING GUIDELINES:
1. GROUND FACTUAL CLAIMS IN EVIDENCE: All assertions must cite exact signal ID strings ("evidence_a_ids" and "evidence_b_ids") from the user profiles. Do NOT invent traits, motivations, or behaviors.
2. OPEN-ENDED ANALYSIS: Identify organic compatibility patterns, complementary relationships, shared similarities, tensions, and uncertainties. You are NOT restricted to predefined profile dimensions.
3. RECIPROCAL FULFILLMENT (`complementary_alignments`): Highlight specific instances where Person A's wants/needs are satisfied by Person B's self/provides (and vice-versa).
   Format: "A seeks [X] -> B provides/embodies [Y]"
4. SHARED ALIGNMENTS (`shared_alignments`): List genuine similarities, shared values, and mutual lifestyle habits.
5. PREVENT OVER-INFERENCE & UNSUPPORTED CLAIMS: If a trait is ambiguous or merely plausible, record it under "uncertainties" — do NOT stretch interpretations into false alignments.

USER A PROFILE:
{user_a_profile}

USER B PROFILE:
{user_b_profile}

OUTPUT FORMAT REQUIREMENT:
You MUST return your response ONLY as a JSON object matching this EXACT format:
```json
{{
  "overall_verdict": "strong_alignment",
  "overall_reasoning": "Executive conclusion highlighting organic synergies and main friction points.",
  "dimension_results": {{
    "emotional_needs": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q2_emotional_needs_s_emotional_needs_00"],
      "evidence_b_ids": ["q2_emotional_needs_s_provides_00"],
      "reasoning": "Explanation of emotional support alignment based on cited evidence."
    }},
    "core_values": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q4_lifestyle_values_s_values_00"],
      "evidence_b_ids": ["q4_lifestyle_values_s_values_00"],
      "reasoning": "Explanation of shared core values and goals based on cited evidence."
    }},
    "lifestyle": {{
      "verdict": "partial_alignment",
      "evidence_a_ids": ["q4_lifestyle_values_s_lifestyle_00"],
      "evidence_b_ids": ["q4_lifestyle_values_s_lifestyle_00"],
      "reasoning": "Explanation of daily habits and lifestyle alignment."
    }},
    "conflict_style": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q3_conflict_provides_s_conflict_style_00"],
      "evidence_b_ids": ["q3_conflict_provides_s_conflict_style_00"],
      "reasoning": "Explanation of conflict resolution alignment."
    }}
  }},
  "complementary_alignments": [
    "A seeks [X] -> B provides [Y]"
  ],
  "shared_alignments": [
    "Both share interest/value in [Z]"
  ],
  "potential_conflicts": [
    "Potential friction point between A and B"
  ],
  "dealbreaker_violations": [],
  "uncertainties": []
}}
```"""
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
