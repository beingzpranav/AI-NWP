"""
Machine Learning models module.
Provides:
- WeatherRandomForest (Random Forest nonlinear baseline)
- WeatherXGBoost (Primary gradient boosting model)
- WeatherAdaBoost (Adaptive boosting model)
- DynamicModelWeighter (Error-based dynamic NWP & ML weighting)
- TwoHeadWeatherNet & WeatherNeuralNetwork (Two-Head ANN for forecast + uncertainty)
"""
import sys
from pathlib import Path

# Add backend directory to sys.path if not present
backend_dir = str(Path(__file__).parent.parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.models.base import BaseWeatherModel
from app.ml.models.random_forest import WeatherRandomForest
from app.ml.models.xgboost_model import WeatherXGBoost
from app.ml.models.adaboost import WeatherAdaBoost
from app.ml.models.dynamic_weighting import (
    DynamicModelWeighter,
    DynamicWeights,
    ModelErrorTracker,
    FALLBACK_WEIGHTS,
)
from app.ml.models.neural_network import (
    TwoHeadWeatherNet,
    WeatherNeuralNetwork,
    heteroscedastic_nll_loss,
)

__all__ = [
    "BaseWeatherModel",
    "WeatherRandomForest",
    "WeatherXGBoost",
    "WeatherAdaBoost",
    "DynamicModelWeighter",
    "DynamicWeights",
    "ModelErrorTracker",
    "FALLBACK_WEIGHTS",
    "TwoHeadWeatherNet",
    "WeatherNeuralNetwork",
    "heteroscedastic_nll_loss",
]
