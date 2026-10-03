"""SQLAlchemy ORM models — Weather Observations."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, DateTime, String,
    Boolean, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class WeatherObservation(Base):
    """Historical / real-time weather observations (any source)."""
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(50), nullable=False, default="station")  # station, synop, etc.

    # Atmospheric
    temperature_c = Column(Float, nullable=True)
    feels_like_c = Column(Float, nullable=True)
    dew_point_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    pressure_hpa = Column(Float, nullable=True)

    # Wind
    wind_speed_kmh = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    wind_gust_kmh = Column(Float, nullable=True)

    # Precipitation
    precipitation_mm = Column(Float, nullable=True)
    precipitation_1h_mm = Column(Float, nullable=True)

    # Radiation / visibility
    solar_radiation_wm2 = Column(Float, nullable=True)
    visibility_m = Column(Float, nullable=True)
    cloud_cover_pct = Column(Float, nullable=True)

    quality_flag = Column(String(10), default="OK")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    location = relationship("Location", back_populates="weather_observations")

    __table_args__ = (
        Index("ix_obs_location_time", "location_id", "observed_at"),
    )


class WeatherUnionObservation(Base):
    """Observations ingested from Weather Union API."""
    __tablename__ = "weather_union_observations"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    station_id = Column(String(100), nullable=False, index=True)
    station_name = Column(String(200), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    # Measured variables
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    pressure_hpa = Column(Float, nullable=True)

    # Station metadata
    station_latitude = Column(Float, nullable=True)
    station_longitude = Column(Float, nullable=True)

    is_valid = Column(Boolean, default=True)
    raw_response = Column(String, nullable=True)  # store raw JSON for debugging

    location = relationship("Location", back_populates="weather_union_observations")

    __table_args__ = (
        Index("ix_wu_station_time", "station_id", "observed_at"),
        Index("ix_wu_location_time", "location_id", "observed_at"),
    )
