"""Pydantic schemas for Weather Union API data."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WeatherUnionObservationData(BaseModel):
    """Normalized Weather Union observation."""
    station_id: str
    station_name: str = ""
    latitude: float
    longitude: float
    observed_at: datetime

    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    rain_intensity_mmph: Optional[float] = None
    light_intensity_lux: Optional[float] = None

    raw_payload: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WeatherUnionStationData(BaseModel):
    """Weather Union station metadata."""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    city: Optional[str] = None
    locality: Optional[str] = None
    is_active: bool = True


class WeatherUnionStatusResponse(BaseModel):
    """Status response for the Weather Union integration."""
    connected: bool
    api_key_set: bool
    last_check: Optional[str] = None
    data_received: Optional[bool] = None
    error: Optional[str] = None
    reason: Optional[str] = None
