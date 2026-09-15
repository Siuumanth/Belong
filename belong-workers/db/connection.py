import os
from contextlib import asynccontextmanager
import psycopg_pool
from config import settings

DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

pool: psycopg_pool.AsyncConnectionPool | None = None

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
