"""Random Forest model wrapper."""
import numpy as np
import joblib
from pathlib import Path
from typing import Optional, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from app.core.logging import get_logger

logger = get_logger(__name__)


class WeatherRandomForest:
    """
    Random Forest wrapper for weather forecasting.
    Supports both single-target and multi-output regression.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: Optional[int] = None,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        max_features: str = "sqrt",
        n_jobs: int = -1,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.n_jobs = n_jobs
        self.random_state = random_state
        self.model: Optional[RandomForestRegressor] = None
        self.feature_names_: list = []
        self.is_fitted: bool = False

    def build(self) -> RandomForestRegressor:
        return RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            max_features=self.max_features,
            n_jobs=self.n_jobs,
            random_state=self.random_state,
            oob_score=True,
        )

    def fit(self, X, y, feature_names: list = None) -> "WeatherRandomForest":
        logger.info("rf_training_start", n_samples=len(X), n_features=X.shape[1])
        self.model = self.build()
        self.model.fit(X, y)
        self.feature_names_ = feature_names or list(range(X.shape[1]))
        self.is_fitted = True
        logger.info("rf_training_done", oob_score=self.model.oob_score_)
        return self

    def predict(self, X) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        return self.model.predict(X)

    def feature_importances(self) -> dict:
        if not self.is_fitted:
            return {}
        importances = self.model.feature_importances_
        return dict(sorted(
            zip(self.feature_names_, importances),
            key=lambda x: x[1], reverse=True
        ))

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("rf_saved", path=path)

    @classmethod
    def load(cls, path: str) -> "WeatherRandomForest":
        obj = joblib.load(path)
        logger.info("rf_loaded", path=path)
        return obj
