import sys
from pathlib import Path
backend_dir = str(Path(__file__).parent.parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.features.engineer import (
    build_feature_matrix,
    add_temporal_features,
    add_lag_features,
    add_rolling_features,
    add_nwp_disagreement_features,
    add_weather_union_bias_features,
    add_source_availability_flags,
    TARGET_VARIABLES,
    LAG_HOURS,
    ROLLING_WINDOWS,
)

__all__ = [
    "build_feature_matrix",
    "add_temporal_features",
    "add_lag_features",
    "add_rolling_features",
    "add_nwp_disagreement_features",
    "add_weather_union_bias_features",
    "add_source_availability_flags",
    "TARGET_VARIABLES",
    "LAG_HOURS",
    "ROLLING_WINDOWS",
]
