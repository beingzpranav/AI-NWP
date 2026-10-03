"""Engineered feature cache model."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EngineeredFeature(Base):
    """Cache of engineered feature vectors — avoids recomputation."""
    __tablename__ = "engineered_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    feature_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feature_vector: Mapped[dict] = mapped_column(JSON, nullable=False)
    feature_version: Mapped[str] = mapped_column(Integer, default="1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_features_location_time", "location_id", "feature_time"),
    )
