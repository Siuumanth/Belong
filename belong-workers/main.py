"""
belong-workers entrypoint.
RabbitMQ consumer loop will be wired here in Phase 6.
"""
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("belong-workers")

if __name__ == "__main__":
    logger.info("belong-workers: not yet implemented. Waiting for Phase 6.")
