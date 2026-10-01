import os

class WorkerSettings:
    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "belong")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "belong_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "belong_password")

    # RabbitMQ (to be configured when Phase 6 is implemented)
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "belong.jobs")
    RABBITMQ_QUEUE_EMBEDDING: str = os.getenv("RABBITMQ_QUEUE_EMBEDDING", "belong.embedding")
    RABBITMQ_QUEUE_MATCHING: str = os.getenv("RABBITMQ_QUEUE_MATCHING", "belong.matching")

    # LLM (Groq default)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Configurable Prompt Templates
    PAIRWISE_REASONING_PROMPT_TEMPLATE: str = os.getenv(
        "PAIRWISE_REASONING_PROMPT_TEMPLATE",
        """You are an expert AI compatibility matchmaking reasoning agent for Belong.
Your task is to analyze complete user evidence packages for User A (the user receiving this report) and User B (their matched candidate) to determine their relational compatibility.

PERSPECTIVE & VOICE INSTRUCTIONS (CRITICAL):
- Write ALL reasoning, executive conclusions (`overall_reasoning`), dimension explanations, alignments, and friction points directly TO User A in the second-person ("You").
- Refer to User B by their name (e.g. "Alex") or as "your candidate" / "they".
- NEVER write in cold third-person system report style like "User A and User B..." or "The LLM finds...".
- Address the user naturally:
  - Good: "You and Alex both prioritize clear communication and daily outdoor activity."
  - Good: "You seek a patient listener during stressful moments, which Alex provides through steady, calm presence."
  - Bad: "User A requires quiet support which User B provides."

INPUT EVIDENCE STRUCTURE:
Each user profile includes:
- Structured signals (`self`, `wants`, `constraints`)
- `other_signals`: Emergent or unmapped signals that don't fit standard dimensions
- `original_responses`: The user's raw onboarding answers preserving exact nuance and context

REASONING GUIDELINES:
1. GROUND FACTUAL CLAIMS IN EVIDENCE: All assertions must cite exact signal ID strings ("evidence_a_ids" and "evidence_b_ids") from the user profiles. Do NOT invent traits, motivations, or behaviors.
2. OPEN-ENDED ANALYSIS: Identify organic compatibility patterns, complementary relationships, shared similarities, tensions, and uncertainties. You are NOT restricted to predefined profile dimensions.
3. RECIPROCAL FULFILLMENT (`complementary_alignments`): Highlight specific instances where what You seek is satisfied by your candidate's self/provides (and vice-versa).
   Format: "You seek [X] -> [Candidate] provides [Y]"
4. SHARED ALIGNMENTS (`shared_alignments`): List genuine similarities, shared values, and mutual lifestyle habits between You and your candidate.
5. PREVENT OVER-INFERENCE & UNSUPPORTED CLAIMS: If a trait is ambiguous or merely plausible, record it under "uncertainties" — do NOT stretch interpretations into false alignments.

USER A PROFILE (Target User - "You"):
{user_a_profile}

USER B PROFILE (Matched Candidate):
{user_b_profile}

OUTPUT FORMAT REQUIREMENT:
You MUST return your response ONLY as a JSON object matching this EXACT format:
```json
{{
  "overall_verdict": "strong_alignment",
  "overall_reasoning": "Executive summary conclusion addressed directly to you ('You') explaining overall compatibility and key synergies with your candidate.",
  "dimension_results": {{
    "emotional_needs": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q2_emotional_needs_s_emotional_needs_00"],
      "evidence_b_ids": ["q2_emotional_needs_s_provides_00"],
      "reasoning": "Explanation of emotional support alignment written directly to you based on cited evidence."
    }},
    "core_values": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q4_lifestyle_values_s_values_00"],
      "evidence_b_ids": ["q4_lifestyle_values_s_values_00"],
      "reasoning": "Explanation of shared core values and goals written directly to you."
    }},
    "lifestyle": {{
      "verdict": "partial_alignment",
      "evidence_a_ids": ["q4_lifestyle_values_s_lifestyle_00"],
      "evidence_b_ids": ["q4_lifestyle_values_s_lifestyle_00"],
      "reasoning": "Explanation of daily habits and lifestyle alignment written directly to you."
    }},
    "conflict_style": {{
      "verdict": "strong_alignment",
      "evidence_a_ids": ["q3_conflict_provides_s_conflict_style_00"],
      "evidence_b_ids": ["q3_conflict_provides_s_conflict_style_00"],
      "reasoning": "Explanation of conflict resolution alignment written directly to you."
    }}
  }},
  "complementary_alignments": [
    "You seek [X] -> [Candidate] provides [Y]"
  ],
  "shared_alignments": [
    "You and [Candidate] both share interest/value in [Z]"
  ],
  "potential_conflicts": [
    "Potential friction point between you and [Candidate]"
  ],
  "dealbreaker_violations": [],
  "uncertainties": []
}}
```"""
    )

    # Embeddings
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_CONFIDENCE_THRESHOLD: float = float(os.getenv("EMBEDDING_CONFIDENCE_THRESHOLD", "0.5"))
    USE_LOCAL_EMBEDDINGS: bool = os.getenv("USE_LOCAL_EMBEDDINGS", "true").lower() == "true"

settings = WorkerSettings()
