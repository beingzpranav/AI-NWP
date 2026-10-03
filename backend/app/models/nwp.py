"""NWP forecast model storage."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NWPForecast(Base):
    """Stores raw NWP model output for a specific location and forecast time."""
    __tablename__ = "nwp_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)

    # model: "gfs", "ecmwf", "jma"
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # When the forecast was generated (run time)
    run_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # The time this forecast is valid for (target time)
    valid_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Forecast horizon in hours
    horizon_h: Mapped[int] = mapped_column(Integer, nullable=False)

    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float)
    precipitation_mm: Mapped[float | None] = mapped_column(Float)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float)
    dew_point_c: Mapped[float | None] = mapped_column(Float)
    visibility_km: Mapped[float | None] = mapped_column(Float)
    solar_radiation_wm2: Mapped[float | None] = mapped_column(Float)
    wind_gusts_ms: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    location: Mapped["Location"] = relationship("Location", back_populates="nwp_forecasts")

    __table_args__ = (
        Index("ix_nwp_location_model_valid", "location_id", "model_name", "valid_time"),
        Index("ix_nwp_valid_time", "valid_time"),
        Index("ix_nwp_run_time", "run_time"),
    )
