"""
Weather AI Platform — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_db
from app.services.ingestion.seed import seed_locations
from app.api import health, locations, forecast, weather, models

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("app_startup", environment=settings.environment)
    try:
        await init_db()
        await seed_locations()
        logger.info("database_initialized_and_seeded")
    except Exception as e:
        logger.warning("database_init_failed", error=str(e),
                       note="App will still start; check DB connection")

    if not settings.weather_union_key_configured:
        logger.warning(
            "weather_union_not_configured",
            message="Set WEATHER_UNION_API_KEY in .env to enable Weather Union integration",
        )
    else:
        logger.info("weather_union_configured")

    yield

    logger.info("app_shutdown")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Adaptive AI–NWP Multi-Model Weather Forecasting & Correction Platform. "
        "Combines GFS, ECMWF, JMA, Weather Union, and ML ensemble forecasting."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging middleware ─────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration,
    )
    return response


# ── Global exception handler ───────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )

# ── Routes ─────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(weather.router, prefix="/api")
app.include_router(models.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/health",
    }
