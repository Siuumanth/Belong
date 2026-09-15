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

    # LLM (same as belong-api, swappable)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # Embeddings
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSIONS: int = 384

settings = WorkerSettings()
