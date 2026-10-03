"""Forecast API endpoints."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.location import Location
from app.services.forecasting import get_forecasting_engine
from app.schemas.weather import ForecastResponse, LocationResponse
from app.core.logging import get_logger

router = APIRouter(prefix="/forecast", tags=["forecast"])
logger = get_logger(__name__)


@router.get("/", response_model=ForecastResponse)
async def get_forecast_by_coordinates(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    hours: int = Query(48, ge=1, le=168, description="Forecast horizon in hours"),
    city: Optional[str] = Query(None, description="Optional city name"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a forecast for arbitrary lat/lon coordinates."""
    engine = get_forecasting_engine()
    loc_response = None
    try:
        # Check if coordinates match an existing saved location in DB
        result = await db.execute(
            select(Location).where(
                Location.latitude.between(lat - 0.25, lat + 0.25),
                Location.longitude.between(lon - 0.25, lon + 0.25),
            )
        )
        matched_loc = result.scalars().first()
        if not matched_loc and city:
            c_result = await db.execute(
                select(Location).where(Location.city.ilike(f"%{city}%"))
            )
            matched_loc = c_result.scalars().first()

        if matched_loc:
            loc_response = LocationResponse(
                id=matched_loc.id,
                name=matched_loc.name,
                city=matched_loc.city,
                country=matched_loc.country,
                latitude=matched_loc.latitude,
                longitude=matched_loc.longitude,
                elevation_m=matched_loc.elevation_m,
                timezone=matched_loc.timezone,
                is_active=matched_loc.is_active,
                created_at=matched_loc.created_at,
            )

        forecast = await engine.generate_forecast(
            lat, lon, forecast_hours=hours, location_response=loc_response
        )
        return forecast
    except Exception as e:
        logger.error("forecast_error", lat=lat, lon=lon, error=str(e))
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")


@router.get("/{location_id}", response_model=ForecastResponse)
async def get_forecast_by_location(
    location_id: int,
    hours: int = Query(48, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Generate a forecast for a saved location."""
    result = await db.execute(select(Location).where(Location.id == location_id))
    loc = result.scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    loc_response = LocationResponse(
        id=loc.id,
        name=loc.name,
        city=loc.city,
        country=loc.country,
        latitude=loc.latitude,
        longitude=loc.longitude,
        elevation_m=loc.elevation_m,
        timezone=loc.timezone,
        is_active=loc.is_active,
        created_at=loc.created_at,
    )

    engine = get_forecasting_engine()
    try:
        return await engine.generate_forecast(
            loc.latitude, loc.longitude,
            forecast_hours=hours,
            location_response=loc_response,
        )
    except Exception as e:
        logger.error("forecast_location_error", location_id=location_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{location_id}/hourly", response_model=ForecastResponse)
async def get_hourly_forecast(
    location_id: int,
    db: AsyncSession = Depends(get_db),
):
    """24-hour hourly forecast for a location."""
    return await get_forecast_by_location(location_id, hours=24, db=db)
