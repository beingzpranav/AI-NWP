"""Current weather & observation endpoints."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.location import Location
from app.models.observation import WeatherObservation, WeatherUnionObservation
from app.schemas.weather import (
    WeatherObservationResponse, WeatherUnionObservationResponse,
    CurrentConditions, LocationResponse, WeatherUnionStatus,
)
from app.services.weather_union import get_weather_union_client
from app.services.nwp import get_nwp_client
from app.core.logging import get_logger

router = APIRouter(prefix="/weather", tags=["weather"])
logger = get_logger(__name__)


@router.get("/current", response_model=CurrentConditions)
async def get_current_conditions(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """Get current conditions from NWP + Weather Union for a coordinate."""
    now = datetime.now(tz=timezone.utc)
    wu_client = get_weather_union_client()
    nwp_client = get_nwp_client()

    # Fetch NWP current (horizon=0)
    nwp_data = await nwp_client.fetch_model_forecast("GFS", lat, lon, forecast_hours=1)
    current_nwp = nwp_data[0] if nwp_data else None

    # Fetch Weather Union
    wu_obs = await wu_client.get_locality_weather(lat, lon)

    loc = LocationResponse(
        id=0, name="Custom Location",
        latitude=lat, longitude=lon,
        is_active=True, created_at=now, timezone="UTC",
    )

    return CurrentConditions(
        location=loc,
        observed_at=now,
        source="NWP+WeatherUnion" if wu_obs else "NWP",
        temperature_c=wu_obs.temperature_c if wu_obs and wu_obs.temperature_c
                      else (current_nwp.temperature_c if current_nwp else None),
        humidity_pct=wu_obs.humidity_pct if wu_obs and wu_obs.humidity_pct
                     else (current_nwp.humidity_pct if current_nwp else None),
        pressure_hpa=current_nwp.pressure_hpa if current_nwp else None,
        wind_speed_kmh=wu_obs.wind_speed_kmh if wu_obs and wu_obs.wind_speed_kmh
                       else (current_nwp.wind_speed_kmh if current_nwp else None),
        wind_direction_deg=wu_obs.wind_direction_deg if wu_obs else (
            current_nwp.wind_direction_deg if current_nwp else None),
        precipitation_mm=wu_obs.rain_accumulation_mm if wu_obs else (
            current_nwp.precipitation_mm if current_nwp else None),
        weather_union_available=wu_obs is not None and wu_obs.is_valid,
        weather_union_temp=wu_obs.temperature_c if wu_obs else None,
        weather_union_station=wu_obs.station_name if wu_obs else None,
    )


@router.get("/weather-union/status", response_model=WeatherUnionStatus)
async def weather_union_status(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
):
    """
    Check Weather Union API status.
    Always tests connectivity using a known WU-covered location.
    Does NOT expose the API key.
    """
    wu_client = get_weather_union_client()
    configured = wu_client.is_configured

    if not configured:
        return WeatherUnionStatus(
            configured=False,
            connected=False,
            message="Weather Union API key not configured. Set WEATHER_UNION_API_KEY in .env",
        )

    # Test connectivity — try user's coords first, fall back to Bengaluru (known coverage)
    test_coords = [(lat, lon)] if (lat is not None and lon is not None) else []
    # Add known WU-covered cities as fallback test points
    test_coords += [
        (12.9716, 77.5946),  # Bengaluru
        (19.0760, 72.8777),  # Mumbai
        (17.3850, 78.4867),  # Hyderabad
    ]

    obs = None
    for test_lat, test_lon in test_coords:
        obs = await wu_client.get_locality_weather(test_lat, test_lon)
        if obs and obs.is_valid:
            break

    connected = obs is not None and obs.is_valid
    return WeatherUnionStatus(
        configured=True,
        connected=connected,
        last_observation_at=obs.fetched_at if connected else None,
        station_count=1 if connected else 0,
        message=(
            f"Connected and receiving observations ({obs.temperature_c:.1f}C)"
            if connected
            else "Configured but no nearby WU station found"
        ),
    )


@router.get("/history/{location_id}", response_model=List[WeatherObservationResponse])
async def get_weather_history(
    location_id: int,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(WeatherObservation)
        .where(WeatherObservation.location_id == location_id)
        .where(WeatherObservation.observed_at >= cutoff)
        .order_by(desc(WeatherObservation.observed_at))
        .limit(500)
    )
    return result.scalars().all()
