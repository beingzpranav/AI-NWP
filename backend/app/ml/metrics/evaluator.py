"""
Compatibility shim — re-exports from evaluation.py.
Legacy code that imports from evaluator.py will still work.
"""
from app.ml.metrics.evaluation import (
    ModelMetrics,
    AblationStudy,
    evaluate_model,
    safe_mae,
    safe_rmse,
    safe_r2,
    safe_mape,
)

__all__ = [
    "ModelMetrics",
    "AblationStudy",
    "evaluate_model",
    "safe_mae",
    "safe_rmse",
    "safe_r2",
    "safe_mape",
]
