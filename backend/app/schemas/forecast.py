"""Additional Pydantic schemas for forecast responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class HealthSchema(BaseModel):
    status: str
    timestamp: str
    app: str
    environment: str
    weather_union_configured: bool


class AblationResultSchema(BaseModel):
    experiment: str
    model: str
    variable: str
    horizon_hours: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    r2: Optional[float] = None
    mape: Optional[float] = None
    absolute_improvement_vs_baseline: Optional[float] = None
    percent_improvement_vs_baseline: Optional[float] = None


class TrainingStatusSchema(BaseModel):
    trained: bool
    version: Optional[str] = None
    trained_at: Optional[str] = None
    target_var: Optional[str] = None
    horizon_hours: Optional[int] = None
    n_features: Optional[int] = None
    metrics: Optional[Dict[str, Any]] = None
