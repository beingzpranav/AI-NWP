import sys
from pathlib import Path
backend_dir = str(Path(__file__).parent.parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.metrics.evaluation import (
    ModelMetrics,
    evaluate_model,
    AblationStudy,
    safe_mae,
    safe_rmse,
    safe_r2,
    safe_mape,
)

__all__ = [
    "ModelMetrics",
    "evaluate_model",
    "AblationStudy",
    "safe_mae",
    "safe_rmse",
    "safe_r2",
    "safe_mape",
]
