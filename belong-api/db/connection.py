import os
from contextlib import asynccontextmanager

try:
    import psycopg_pool
    from psycopg_pool import AsyncConnectionPool
except (ImportError, ModuleNotFoundError):
    psycopg_pool = None
    AsyncConnectionPool = None

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "belong")
DB_USER = os.getenv("POSTGRES_USER", "belong_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "belong_password")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Connection pool instance (can be initialized on FastAPI startup)
pool = None

async def init_pool():
    global pool
    if pool is None:
        pool = psycopg_pool.AsyncConnectionPool(
            conninfo=DATABASE_URL,
            min_size=2,
            max_size=10,
            open=False,
        )
        await pool.open()

async def close_pool():
    global pool
    if pool is not None:
        await pool.close()
        pool = None

@asynccontextmanager
async def get_db_connection():
    if pool is None:
        await init_pool()
    async with pool.connection() as conn:
        yield conn
