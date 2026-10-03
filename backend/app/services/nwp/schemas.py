"""NWP data schemas."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NWPForecastPoint(BaseModel):
    """A single hourly NWP forecast value."""
    valid_time: datetime
    horizon_h: int
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    dew_point_c: Optional[float] = None
    visibility_km: Optional[float] = None
    solar_radiation_wm2: Optional[float] = None
    wind_gusts_ms: Optional[float] = None
    feels_like_c: Optional[float] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class NWPModelForecast(BaseModel):
    """Full NWP forecast from a single model."""
    model_name: str  # gfs | ecmwf | jma
    latitude: float
    longitude: float
    run_time: datetime
    points: List[NWPForecastPoint]

    @property
    def available(self) -> bool:
        return len(self.points) > 0

    def get_point_at_horizon(self, horizon_h: int) -> Optional[NWPForecastPoint]:
        for p in self.points:
            if p.horizon_h == horizon_h:
                return p
        return None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
