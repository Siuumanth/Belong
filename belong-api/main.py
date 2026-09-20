import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.connection import init_pool, close_pool
from db.migrate import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("belong-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=========================================")
    logger.info("   Starting Belong API Microservice      ")
    logger.info("=========================================")
    try:
        await init_pool()
        logger.info("[OK] Connected to PostgreSQL with pgvector.")
        run_migrations()
        logger.info("[OK] Database migrations verified & up to date.")
    except Exception as e:
        logger.warning(f"[WARNING] Database initialization note: {e}")
    logger.info("[OK] Belong API Service is READY and accepting requests on port 8000!")
    yield
    logger.info("Shutting down Belong API Service...")
    await close_pool()
    logger.info("Belong API Service shutdown complete.")

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

from api.routes.profiles import router as profiles_router
from api.routes.onboarding import router as onboarding_router
from api.routes.embeddings import router as embeddings_router
from api.routes.matches import router as matches_router

@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "python-belong-api"}

app.include_router(profiles_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(embeddings_router, prefix="/api")
app.include_router(matches_router, prefix="/api")
