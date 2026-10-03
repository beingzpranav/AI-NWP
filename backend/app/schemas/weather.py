"""Pydantic response/request schemas for weather data."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LocationBase(BaseModel):
    name: str
    city: Optional[str] = None
    country: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    elevation_m: Optional[float] = None
    timezone: str = "UTC"


class LocationCreate(LocationBase):
    pass


class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


class WeatherObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_id: int
    observed_at: datetime
    source: str
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    visibility_m: Optional[float] = None
    cloud_cover_pct: Optional[float] = None


class WeatherUnionObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    location_id: int
    station_id: str
    station_name: Optional[str] = None
    observed_at: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    pressure_hpa: Optional[float] = None
    is_valid: bool


class NWPForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    model_name: str
    valid_time: datetime
    horizon_hours: int
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    precipitation_mm: Optional[float] = None
    pressure_hpa: Optional[float] = None


class UncertaintyBands(BaseModel):
    temperature_sigma: Optional[float] = None
    humidity_sigma: Optional[float] = None
    wind_speed_sigma: Optional[float] = None
    precipitation_sigma: Optional[float] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class ModelWeights(BaseModel):
    gfs: float
    ecmwf: float
    jma: float
    ml: float

    def model_post_init(self, __context) -> None:
        total = self.gfs + self.ecmwf + self.jma + self.ml
        if abs(total - 1.0) >= 0.05:
            import logging
            logging.getLogger(__name__).warning(f"ModelWeights sum={total:.3f} (expected ~1.0)")


class ForecastPoint(BaseModel):
    valid_time: datetime
    horizon_hours: int
    # HEAD 1 — weather prediction
    temperature_c: Optional[float] = None
    actual_temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    pressure_hpa: Optional[float] = None
    # HEAD 2 — uncertainty
    uncertainty: Optional[UncertaintyBands] = None
    # Component forecasts for comparison
    gfs: Optional[NWPForecastResponse] = None
    ecmwf: Optional[NWPForecastResponse] = None
    jma: Optional[NWPForecastResponse] = None
    # Dynamic weights
    weights: Optional[ModelWeights] = None


class ForecastResponse(BaseModel):
    location: LocationResponse
    generated_at: datetime
    forecast_hours: int
    data_sources: dict
    points: List[ForecastPoint]


class ModelPerformanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    model_name: str
    variable: str
    horizon_hours: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    mape: Optional[float] = None
    sample_count: Optional[int] = None
    evaluated_at: datetime


class WeatherUnionStatus(BaseModel):
    configured: bool
    connected: bool
    last_observation_at: Optional[datetime] = None
    station_count: int = 0
    message: str


class CurrentConditions(BaseModel):
    location: LocationResponse
    observed_at: datetime
    source: str
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    visibility_m: Optional[float] = None
    weather_union_available: bool = False
    weather_union_temp: Optional[float] = None
    weather_union_station: Optional[str] = None
