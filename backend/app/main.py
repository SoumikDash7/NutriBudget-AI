# ── Bootstrap logging FIRST — must be before any other app import ─────────
# Uvicorn configures its own handlers before main.py runs, so we import
# setup_logging alone first, apply it, then import everything else.
import logging as _logging
from app.core.logging import get_logger, setup_logging  # noqa: E402
from app.core.config import settings  # noqa: E402

setup_logging(
    level=_logging.DEBUG if settings.APP_ENV == "development" else _logging.INFO,
    log_file="logs/app.log" if settings.APP_ENV != "development" else None,
)

# ── Now import the rest of the app ────────────────────────────────────────
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.api import api_router
from app.core.handlers import register_exception_handlers
from app.db.session import engine

logger = get_logger(__name__)

# Configure CORS origins list (used in lifespan and middleware)
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")] if settings.ALLOWED_ORIGINS else []

# ── Lifespan event handler ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}  [{settings.APP_ENV}]")
    logger.info(f"CORS origins: {origins}")
    
    app.state.http_client = httpx.AsyncClient()
    
    openrouter_ok = bool(settings.OPENROUTER_API_KEY)
    groq_ok       = bool(settings.GROQ_API_KEY)
    hf_ok         = bool(settings.HUGGINGFACE_API_KEY)
    usda_ok       = bool(settings.USDA_API_KEY)
    logger.info(
        f"AI keys loaded - "
        f"OpenRouter: {'OK' if openrouter_ok else 'MISSING'}  "
        f"Groq: {'OK' if groq_ok else 'MISSING'}  "
        f"HuggingFace: {'OK' if hf_ok else 'MISSING'}  "
        f"USDA: {'OK' if usda_ok else 'MISSING'}"
    )
    yield
    # Shutdown
    await app.state.http_client.aclose()
    logger.info(f"{settings.APP_NAME} shutting down.")

# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Powered Nutrition & Budget Management API",
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router, prefix="/api/v1")


# ── Request / Response logging middleware ─────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    method = request.method
    path   = request.url.path

    logger.debug(f"> {method} {path}")

    response = await call_next(request)

    elapsed_ms = (time.perf_counter() - start) * 1000
    status     = response.status_code

    # Colour-code by status range
    if status < 300:
        logger.info(f"< {method} {path}  [{status}]  {elapsed_ms:.1f}ms")
    elif status < 400:
        logger.info(f"< {method} {path}  [{status}]  {elapsed_ms:.1f}ms")
    elif status < 500:
        logger.warning(f"< {method} {path}  [{status}]  {elapsed_ms:.1f}ms")
    else:
        logger.error(f"< {method} {path}  [{status}]  {elapsed_ms:.1f}ms")

    return response


# ── Lifecycle events migrated to lifespan handler ─────────────────────────────


# ── Health endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "NutriBudget AI Backend Running [*]",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/db", tags=["Health"])
async def database_health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.debug("DB health check: OK")
        return {"status": "healthy", "database": "connected"}

    except Exception as e:
        logger.error(f"DB health check failed: {e}", exc_info=True)
        return {"status": "unhealthy", "database": "failed", "error": str(e)}


@app.get("/health/ai", tags=["Health"])
async def ai_health():
    return {
        "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
        "groq_configured": bool(settings.GROQ_API_KEY),
        "huggingface_configured": bool(settings.HUGGINGFACE_API_KEY),
        "usda_configured": bool(settings.USDA_API_KEY),
    }