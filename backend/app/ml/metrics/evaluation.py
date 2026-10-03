"""
Model evaluation metrics and comparison framework.
Supports ablation study: NWP-only vs NWP+WU vs NWP+ML vs full hybrid.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelMetrics:
    model_name: str
    variable: str
    horizon_hours: int
    mae: float
    rmse: float
    r2: float
    mape: Optional[float]
    sample_count: int

    def to_dict(self) -> dict:
        return {
            "model": self.model_name,
            "variable": self.variable,
            "horizon_hours": self.horizon_hours,
            "mae": round(self.mae, 4),
            "rmse": round(self.rmse, 4),
            "r2": round(self.r2, 4),
            "mape": round(self.mape, 4) if self.mape is not None else None,
            "sample_count": self.sample_count,
        }


def safe_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    if mask.sum() < 2:
        return np.nan
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask])))


def safe_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    if mask.sum() < 2:
        return np.nan
    return float(np.sqrt(np.mean((y_true[mask] - y_pred[mask]) ** 2)))


def safe_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    if mask.sum() < 2:
        return np.nan
    yt, yp = y_true[mask], y_pred[mask]
    ss_res = np.sum((yt - yp) ** 2)
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 1e-10 else 0.0


def safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    mask = ~(np.isnan(y_true) | np.isnan(y_pred)) & (np.abs(y_true) > 0.1)
    if mask.sum() < 2:
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    variable: str,
    horizon_hours: int,
) -> ModelMetrics:
    return ModelMetrics(
        model_name=model_name,
        variable=variable,
        horizon_hours=horizon_hours,
        mae=safe_mae(y_true, y_pred),
        rmse=safe_rmse(y_true, y_pred),
        r2=safe_r2(y_true, y_pred),
        mape=safe_mape(y_true, y_pred),
        sample_count=int(np.sum(~np.isnan(y_pred))),
    )


class AblationStudy:
    """
    Evaluates system under different configurations to measure
    the actual contribution of Weather Union and ML.

    Experiments:
    - NWP_only: best single NWP model
    - NWP_ensemble: simple average of all NWP
    - NWP_ML: NWP + ML base models (no WU)
    - NWP_WU: NWP + Weather Union correction (no ML)
    - Full_Hybrid: NWP + WU + ML + ANN
    """

    EXPERIMENT_NAMES = [
        "NWP only",
        "NWP + Weather Union",
        "NWP + ML",
        "NWP + ML + Weather Union",
        "NWP + ML + Weather Union + ANN",
    ]

    def __init__(self):
        self.results: Dict[str, List[ModelMetrics]] = {}

    def add_result(self, experiment: str, metrics: ModelMetrics) -> None:
        if experiment not in self.results:
            self.results[experiment] = []
        self.results[experiment].append(metrics)

    def compare(
        self, variable: str, horizon_hours: int
    ) -> List[dict]:
        """Compare all experiments for a given variable and horizon."""
        comparison = []
        for exp, metrics_list in self.results.items():
            for m in metrics_list:
                if m.variable == variable and m.horizon_hours == horizon_hours:
                    d = m.to_dict()
                    d["experiment"] = exp
                    comparison.append(d)

        if not comparison:
            return []

        # Calculate improvement over NWP only baseline
        baseline = next(
            (c for c in comparison if c["experiment"] in ("NWP only", "NWP_only", "RF_baseline")),
            comparison[0]
        )
        b_mae = baseline.get("mae")
        if b_mae is not None:
            for c in comparison:
                c_mae = c.get("mae")
                if c_mae is not None:
                    abs_imp = b_mae - c_mae
                    pct_imp = (abs_imp / b_mae) * 100 if b_mae > 0 else 0.0
                    c["baseline_error"] = round(float(b_mae), 4)
                    c["new_error"] = round(float(c_mae), 4)
                    c["absolute_improvement"] = round(float(abs_imp), 4)
                    c["percentage_improvement"] = round(float(pct_imp), 2)
                    c["absolute_improvement_vs_baseline"] = round(float(abs_imp), 4)
                    c["percent_improvement_vs_baseline"] = round(float(pct_imp), 2)

        return sorted(comparison, key=lambda x: x.get("mae", float("inf")))

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for exp, metrics_list in self.results.items():
            for m in metrics_list:
                d = m.to_dict()
                d["experiment"] = exp
                rows.append(d)
        return pd.DataFrame(rows) if rows else pd.DataFrame()
