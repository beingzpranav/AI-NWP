"""ML prediction and model performance models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime, Float, ForeignKey, Index,
    Integer, JSON, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ForecastRun(Base):
    """Tracks each forecast run with metadata."""
    __tablename__ = "forecast_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending/running/complete/failed
    model_version: Mapped[str | None] = mapped_column(String(100))

    # Source availability flags
    gfs_available: Mapped[bool] = mapped_column(Integer, default=0)
    ecmwf_available: Mapped[bool] = mapped_column(Integer, default=0)
    jma_available: Mapped[bool] = mapped_column(Integer, default=0)
    weather_union_available: Mapped[bool] = mapped_column(Integer, default=0)

    # Dynamic weights used (JSON)
    model_weights: Mapped[dict | None] = mapped_column(JSON)

    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list] = relationship("ModelPrediction", back_populates="forecast_run")

    __table_args__ = (Index("ix_forecast_runs_location_time", "location_id", "run_at"),)


class ModelPrediction(Base):
    """Final corrected forecast output per timestep."""
    __tablename__ = "model_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    forecast_run_id: Mapped[int] = mapped_column(ForeignKey("forecast_runs.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_h: Mapped[int] = mapped_column(Integer, nullable=False)

    # Head 1 — Forecast
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float)
    precipitation_mm: Mapped[float | None] = mapped_column(Float)

    # Head 2 — Uncertainty
    temperature_uncertainty: Mapped[float | None] = mapped_column(Float)
    humidity_uncertainty: Mapped[float | None] = mapped_column(Float)
    pressure_uncertainty: Mapped[float | None] = mapped_column(Float)
    wind_speed_uncertainty: Mapped[float | None] = mapped_column(Float)
    precipitation_uncertainty: Mapped[float | None] = mapped_column(Float)
    overall_confidence: Mapped[float | None] = mapped_column(Float)  # 0-1

    # Individual model predictions (for comparison display)
    gfs_temperature: Mapped[float | None] = mapped_column(Float)
    ecmwf_temperature: Mapped[float | None] = mapped_column(Float)
    jma_temperature: Mapped[float | None] = mapped_column(Float)
    rf_temperature: Mapped[float | None] = mapped_column(Float)
    xgb_temperature: Mapped[float | None] = mapped_column(Float)
    ada_temperature: Mapped[float | None] = mapped_column(Float)
    ensemble_temperature: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    forecast_run: Mapped["ForecastRun"] = relationship("ForecastRun", back_populates="predictions")
    location: Mapped["Location"] = relationship("Location", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_location_valid", "location_id", "valid_time"),
        Index("ix_predictions_run_id", "forecast_run_id"),
    )


class ModelPerformance(Base):
    """Tracks model error metrics over rolling windows — used for dynamic weighting."""
    __tablename__ = "model_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_variable: Mapped[str] = mapped_column(String(100), nullable=False)
    horizon_h: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_days: Mapped[int] = mapped_column(Integer, default=7)

    mae: Mapped[float | None] = mapped_column(Float)
    rmse: Mapped[float | None] = mapped_column(Float)
    mape: Mapped[float | None] = mapped_column(Float)
    r2: Mapped[float | None] = mapped_column(Float)
    n_samples: Mapped[int] = mapped_column(Integer, default=0)
    reliability_score: Mapped[float | None] = mapped_column(Float)
    dynamic_weight: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("ix_perf_location_model_time", "location_id", "model_name", "evaluated_at"),
    )
