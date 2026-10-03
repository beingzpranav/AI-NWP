"""XGBoost model wrapper for weather forecasting."""
import numpy as np
import joblib
from pathlib import Path
from typing import Optional
from xgboost import XGBRegressor
from app.core.logging import get_logger

logger = get_logger(__name__)


class WeatherXGBoost:
    """
    XGBoost gradient boosting model.
    Primary gradient boosting component of the ensemble.
    """

    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        min_child_weight: int = 3,
        gamma: float = 0.1,
        random_state: int = 42,
        n_jobs: int = -1,
        early_stopping_rounds: int = 50,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.min_child_weight = min_child_weight
        self.gamma = gamma
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.early_stopping_rounds = early_stopping_rounds
        self.model: Optional[XGBRegressor] = None
        self.feature_names_: list = []
        self.is_fitted: bool = False

    def build(self) -> XGBRegressor:
        return XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            min_child_weight=self.min_child_weight,
            gamma=self.gamma,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            tree_method="hist",
            eval_metric="rmse",
            verbosity=0,
        )

    def fit(
        self, X_train, y_train, X_val=None, y_val=None, feature_names: list = None
    ) -> "WeatherXGBoost":
        logger.info("xgb_training_start", n_samples=len(X_train))
        self.model = self.build()

        eval_set = [(X_val, y_val)] if X_val is not None else None
        callbacks = []

        self.model.fit(
            X_train, y_train,
            eval_set=eval_set,
            verbose=False,
        )
        self.feature_names_ = feature_names or list(range(X_train.shape[1]))
        self.is_fitted = True
        logger.info("xgb_training_done", best_iter=self.model.best_iteration
                    if hasattr(self.model, "best_iteration") else self.n_estimators)
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
        logger.info("xgb_saved", path=path)

    @classmethod
    def load(cls, path: str) -> "WeatherXGBoost":
        return joblib.load(path)
