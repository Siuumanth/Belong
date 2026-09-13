from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.connection import init_pool, close_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database connection pool
    try:
        await init_pool()
        print("Connected to PostgreSQL with pgvector.")
    except Exception as e:
        print(f"Warning: Could not connect to DB on startup: {e}")
    yield
    # Teardown
    await close_pool()

app = FastAPI(
    title="Belong API Service",
    description="FastAPI service for Belong compatibility matching platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "python-belong-api"}
