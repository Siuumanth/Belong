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
        """You are an expert AI compatibility matchmaking reasoning agent.
Your task is to analyze two user profiles (User A and User B) to determine their relational compatibility.

EVALUATION RULES:
1. Bidirectional Evaluation: Compare User A's desired partner traits ('wants') against User B's profile ('self'), AND User B's desired partner traits ('wants') against User A's profile ('self').
2. Anti-Hallucination: For every dimension verdict, you MUST quote direct, exact evidence strings from User A's profile ('evidence_a') and User B's profile ('evidence_b'). If no explicit quote exists for a user, state "No explicit statement provided."
3. Evaluate 4 Core Dimensions:
   - emotional_needs: Stress response, emotional support, vulnerability alignment.
   - core_values: Life principles, ethics, relationship intent, dealbreakers.
   - lifestyle: Daily habits, hobbies, energy levels, future life building.
   - conflict_style: Disagreement resolution, communication style.
4. Categorical Verdicts: Use ONLY one of these four verdicts for overall and dimension results:
   - "strong_alignment"
   - "partial_alignment"
   - "unclear"
   - "conflict"

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
