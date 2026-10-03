"""Health check endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "app": settings.app_name,
        "environment": settings.environment,
        "weather_union_configured": settings.weather_union_key_configured,
    }
