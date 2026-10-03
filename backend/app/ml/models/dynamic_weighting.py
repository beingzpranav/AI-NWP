"""
Dynamic Model Weighting.

Dynamically calculates reliability weights for GFS, ECMWF, JMA, and the ML ensemble
based on recent measured performance. Weights are NOT hardcoded.

Algorithm:
1. Compute MAE for each NWP model over a recent rolling window
2. Convert errors to reliability scores: reliability = 1 / (MAE + epsilon)
3. Normalize to sum = 1
4. Apply smoothing to prevent rapid weight oscillation
5. Ensure numerically stable computation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from app.core.logging import get_logger

logger = get_logger(__name__)

MODELS = ["GFS", "ECMWF", "JMA", "ML"]
EPSILON = 1e-6  # prevent division by zero
SMOOTHING_ALPHA = 0.3  # exponential smoothing (lower = more stable)
MIN_WEIGHT = 0.05  # ensure every available model gets at least 5%
FALLBACK_WEIGHTS = {"GFS": 0.30, "ECMWF": 0.40, "JMA": 0.20, "ML": 0.10}


@dataclass
class ModelErrorStats:
    model: str
    mae: float
    rmse: float
    r2: float
    sample_count: int
    reliability_score: float = 0.0
    weight: float = 0.0


def compute_mae(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """MAE, ignoring NaN pairs."""
    mask = ~(np.isnan(predictions) | np.isnan(actuals))
    if mask.sum() < 2:
        return np.nan
    return float(np.mean(np.abs(predictions[mask] - actuals[mask])))


def compute_rmse(predictions: np.ndarray, actuals: np.ndarray) -> float:
    mask = ~(np.isnan(predictions) | np.isnan(actuals))
    if mask.sum() < 2:
        return np.nan
    return float(np.sqrt(np.mean((predictions[mask] - actuals[mask]) ** 2)))


def compute_r2(predictions: np.ndarray, actuals: np.ndarray) -> float:
    mask = ~(np.isnan(predictions) | np.isnan(actuals))
    if mask.sum() < 2:
        return np.nan
    p, a = predictions[mask], actuals[mask]
    ss_res = np.sum((a - p) ** 2)
    ss_tot = np.sum((a - np.mean(a)) ** 2)
    if ss_tot < EPSILON:
        return 0.0
    return float(1 - ss_res / ss_tot)


class DynamicModelWeighter:
    """
    Calculates normalized dynamic weights for NWP models + ML based
    on recent forecast performance.

    Usage:
        weighter = DynamicModelWeighter()
        weights = weighter.compute_weights(error_history_df, variable="temperature_c")
    """

    def __init__(
        self,
        window_hours: int = 72,
        smoothing_alpha: float = SMOOTHING_ALPHA,
        min_weight: float = MIN_WEIGHT,
    ):
        self.window_hours = window_hours
        self.smoothing_alpha = smoothing_alpha
        self.min_weight = min_weight
        self._previous_weights: Optional[Dict[str, float]] = None

    def compute_weights(
        self,
        df: pd.DataFrame,
        variable: str = "temperature_c",
        available_models: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Compute dynamic weights from a DataFrame containing columns:
          - timestamp
          - actual_{variable}
          - {model}_{variable}_pred  (for each model)

        Returns a dict: {"GFS": 0.32, "ECMWF": 0.41, "JMA": 0.17, "ML": 0.10}
        Always sums to 1.0.
        """
        if available_models is None:
            available_models = MODELS

        # Filter to recent window
        if "timestamp" in df.columns:
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=self.window_hours)
            df = df[pd.to_datetime(df["timestamp"], utc=True) >= cutoff]

        actual_col = f"actual_{variable}"
        if actual_col not in df.columns or len(df) < 5:
            logger.warning("dynamic_weighting_insufficient_data",
                           variable=variable, rows=len(df))
            return self._fallback(available_models)

        actuals = df[actual_col].values
        error_stats: Dict[str, ModelErrorStats] = {}

        for model in available_models:
            pred_col = f"{model.lower()}_{variable}_pred"
            if pred_col not in df.columns:
                continue
            preds = df[pred_col].values
            mae = compute_mae(preds, actuals)
            rmse = compute_rmse(preds, actuals)
            r2 = compute_r2(preds, actuals)
            if np.isnan(mae):
                continue
            error_stats[model] = ModelErrorStats(
                model=model,
                mae=mae,
                rmse=rmse,
                r2=r2,
                sample_count=int(~np.isnan(preds).sum()),
                reliability_score=1.0 / (mae + EPSILON),
            )

        if not error_stats:
            return self._fallback(available_models)

        # Raw reliability scores
        total_reliability = sum(s.reliability_score for s in error_stats.values())
        raw_weights = {
            m: s.reliability_score / total_reliability
            for m, s in error_stats.items()
        }

        # Apply minimum weight floor
        weights = self._apply_min_weight_floor(raw_weights, available_models)

        # Apply exponential smoothing against previous weights
        if self._previous_weights:
            weights = {
                m: (self.smoothing_alpha * weights.get(m, 0.0)
                    + (1 - self.smoothing_alpha) * self._previous_weights.get(m, 0.0))
                for m in set(list(weights.keys()) + list(self._previous_weights.keys()))
            }
            # Renormalize after smoothing
            total = sum(weights.values())
            weights = {m: w / total for m, w in weights.items()}

        self._previous_weights = weights.copy()

        logger.info(
            "dynamic_weights_computed",
            variable=variable,
            weights={m: round(w, 4) for m, w in weights.items()},
            based_on_rows=len(df),
        )

        return weights

    def _apply_min_weight_floor(
        self, raw_weights: Dict[str, float], available_models: List[str]
    ) -> Dict[str, float]:
        """
        Ensure every available model gets at least min_weight.
        Normalize remaining budget across models that exceed min_weight.
        """
        weights = {m: max(raw_weights.get(m, 0.0), self.min_weight)
                   for m in available_models if m in raw_weights}
        total = sum(weights.values())
        return {m: w / total for m, w in weights.items()}

    def _fallback(self, available_models: List[str]) -> Dict[str, float]:
        """Return default weights when insufficient data."""
        weights = {m: FALLBACK_WEIGHTS.get(m, 0.0) for m in available_models}
        total = sum(weights.values())
        if total < EPSILON:
            n = len(available_models)
            return {m: 1.0 / n for m in available_models}
        return {m: w / total for m, w in weights.items()}

    @staticmethod
    def blend_predictions(
        predictions: Dict[str, float],
        weights: Dict[str, float],
    ) -> float:
        """
        Compute weighted average of model predictions.

        Args:
            predictions: {"GFS": 31.8, "ECMWF": 32.4, "JMA": 31.5, "ML": 32.1}
            weights:     {"GFS": 0.31, "ECMWF": 0.42, "JMA": 0.17, "ML": 0.10}

        Returns:
            Weighted blended prediction value
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for model, pred in predictions.items():
            w = weights.get(model, 0.0)
            if pred is not None and not np.isnan(pred) and w > 0:
                weighted_sum += w * pred
                total_weight += w

        if total_weight < EPSILON:
            available = [v for v in predictions.values() if v is not None and not np.isnan(v)]
            return float(np.mean(available)) if available else np.nan

        return float(weighted_sum / total_weight)
