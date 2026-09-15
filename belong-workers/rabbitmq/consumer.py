# TODO Phase 6: RabbitMQ message consumer + job dispatcher
# - Subscribes to belong.jobs exchange
# - Routes by routing_key: "embedding" → EmbeddingWorker, "matching" → MatchingWorker
# - Ack on success, Nack+requeue on recoverable errors, Dead-letter on permanent failures
