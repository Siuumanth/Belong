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
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Configurable Prompt Templates
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
