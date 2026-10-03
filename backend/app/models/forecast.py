"""SQLAlchemy ORM models — NWP Forecasts & Model Predictions."""
from sqlalchemy import (
    Column, Integer, Float, DateTime, String,
    Boolean, ForeignKey, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class NWPForecast(Base):
    """Raw NWP model forecast data (GFS / ECMWF / JMA)."""
    __tablename__ = "nwp_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    model_name = Column(String(20), nullable=False, index=True)  # GFS, ECMWF, JMA
    run_time = Column(DateTime(timezone=True), nullable=False, index=True)  # model run
    valid_time = Column(DateTime(timezone=True), nullable=False, index=True)  # forecast valid for
    horizon_hours = Column(Integer, nullable=False)

    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    pressure_hpa = Column(Float, nullable=True)
    cloud_cover_pct = Column(Float, nullable=True)

    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    location = relationship("Location", back_populates="nwp_forecasts")

    __table_args__ = (
        Index("ix_nwp_loc_model_valid", "location_id", "model_name", "valid_time"),
    )


class ModelPrediction(Base):
    """Final hybrid ML model predictions."""
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id"), nullable=True)
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    valid_time = Column(DateTime(timezone=True), nullable=False, index=True)
    horizon_hours = Column(Integer, nullable=False)

    # HEAD 1 — Forecast
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)
    wind_direction_deg = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    pressure_hpa = Column(Float, nullable=True)

    # HEAD 2 — Uncertainty
    temperature_uncertainty = Column(Float, nullable=True)
    humidity_uncertainty = Column(Float, nullable=True)
    wind_speed_uncertainty = Column(Float, nullable=True)
    precipitation_uncertainty = Column(Float, nullable=True)

    # Derived confidence [0–1]
    confidence_score = Column(Float, nullable=True)

    # Dynamic weights used
    gfs_weight = Column(Float, nullable=True)
    ecmwf_weight = Column(Float, nullable=True)
    jma_weight = Column(Float, nullable=True)
    ml_weight = Column(Float, nullable=True)

    location = relationship("Location", back_populates="model_predictions")

    __table_args__ = (
        Index("ix_pred_loc_valid", "location_id", "valid_time"),
    )


class ForecastRun(Base):
    """Metadata for each forecast generation run."""
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="running")  # running, completed, failed
    gfs_available = Column(Boolean, default=False)
    ecmwf_available = Column(Boolean, default=False)
    jma_available = Column(Boolean, default=False)
    weather_union_available = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)


class ModelPerformance(Base):
    """Tracked performance metrics per model, location, variable, horizon."""
    __tablename__ = "model_performance"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(50), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)
    variable = Column(String(50), nullable=False)
    horizon_hours = Column(Integer, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    mape = Column(Float, nullable=True)
    sample_count = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_perf_model_var_horizon", "model_name", "variable", "horizon_hours"),
    )
