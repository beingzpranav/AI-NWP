"""
Base class for all weather ML models.
Provides a common interface for fit/predict/save/load.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class BaseWeatherModel(ABC):
    """Abstract base for all weather forecast models."""

    def __init__(self, name: str, target_variables: List[str]):
        self.name = name
        self.target_variables = target_variables
        self.is_fitted = False
        self._feature_names: List[str] = []

    def set_feature_names(self, names: List[str]) -> None:
        self._feature_names = names

    @abstractmethod
    def fit(self, X, y, **kwargs) -> "BaseWeatherModel":
        ...

    @abstractmethod
    def predict(self, X) -> np.ndarray:
        ...

    def predict_with_fallback(self, X) -> np.ndarray:
        """Predict, returning NaN array if model not fitted."""
        if not self.is_fitted:
            return np.full((len(X), len(self.target_variables)), np.nan)
        try:
            return self.predict(X)
        except Exception:
            return np.full((len(X), len(self.target_variables)), np.nan)
