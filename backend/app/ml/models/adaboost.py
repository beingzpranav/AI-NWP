"""AdaBoost model wrapper for weather forecasting."""
import numpy as np
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import AdaBoostRegressor
from sklearn.tree import DecisionTreeRegressor
from app.core.logging import get_logger

logger = get_logger(__name__)


class WeatherAdaBoost:
    """
    AdaBoost regressor for weather forecasting.
    Provides a complementary view to RF and XGBoost.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.1,
        max_depth_base: int = 4,
        loss: str = "linear",
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth_base = max_depth_base
        self.loss = loss
        self.random_state = random_state
        self.model: Optional[AdaBoostRegressor] = None
        self.feature_names_: list = []
        self.is_fitted: bool = False

    def build(self) -> AdaBoostRegressor:
        base = DecisionTreeRegressor(
            max_depth=self.max_depth_base,
            min_samples_leaf=2,
        )
        return AdaBoostRegressor(
            estimator=base,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            loss=self.loss,
            random_state=self.random_state,
        )

    def fit(self, X, y, feature_names: list = None) -> "WeatherAdaBoost":
        logger.info("adaboost_training_start", n_samples=len(X))
        # AdaBoost cannot handle NaN — impute with column means
        import numpy as np
        X = np.array(X, dtype=np.float64)
        col_means = np.nanmean(X, axis=0)
        col_means = np.nan_to_num(col_means, nan=0.0)
        nan_idx = np.isnan(X)
        if np.any(nan_idx):
            X[nan_idx] = np.take(col_means, np.where(nan_idx)[1])
            X = np.nan_to_num(X, nan=0.0)
        y = np.array(y, dtype=np.float64)
        y_nan = np.isnan(y)
        X = X[~y_nan]
        y = y[~y_nan]
        self.model = self.build()
        self.model.fit(X, y)
        self.feature_names_ = feature_names or list(range(X.shape[1]))
        self.is_fitted = True
        logger.info("adaboost_training_done")
        return self

    def predict(self, X) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        return self.model.predict(X)

    def feature_importances(self) -> dict:
        if not self.is_fitted:
            return {}
        scores = self.model.feature_importances_
        return dict(sorted(
            zip(self.feature_names_, scores),
            key=lambda x: x[1], reverse=True
        ))

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "WeatherAdaBoost":
        return joblib.load(path)
