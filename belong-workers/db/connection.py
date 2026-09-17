import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

try:
    import psycopg_pool
    from psycopg_pool import AsyncConnectionPool
except (ImportError, ModuleNotFoundError):
    psycopg_pool = None
    AsyncConnectionPool = None

from config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

pool = None

async def init_pool():
    global pool
    if pool is None and AsyncConnectionPool is not None:
        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=2,
            max_size=10,
            open=False,
        )
        await pool.open()
        logger.info("Worker database connection pool initialized.")

async def close_pool():
    global pool
    if pool is not None:
        await pool.close()
        pool = None
        logger.info("Worker database connection pool closed.")

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator:
    if pool is None:
        await init_pool()
    async with pool.connection() as conn:
        yield conn
