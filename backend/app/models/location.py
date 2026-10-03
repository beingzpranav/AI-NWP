"""SQLAlchemy ORM model — Location."""
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    city = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_m = Column(Float, nullable=True)
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    weather_observations = relationship("WeatherObservation", back_populates="location")
    weather_union_observations = relationship("WeatherUnionObservation", back_populates="location")
    nwp_forecasts = relationship("NWPForecast", back_populates="location")
    model_predictions = relationship("ModelPrediction", back_populates="location")
