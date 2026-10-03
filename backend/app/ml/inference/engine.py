"""
ML Inference Engine for Weather AI Platform.
Loads trained artifacts (Scaler, RF, XGBoost, AdaBoost, Two-Head ANN)
and produces leakage-safe forecasts with heteroscedastic uncertainty and confidence scores.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import joblib
import numpy as np
try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None
    HAS_TORCH = False

from app.core.config import get_settings
from app.ml.features.engineer import build_feature_matrix, TARGET_VARIABLES
from app.ml.models.random_forest import WeatherRandomForest
from app.ml.models.xgboost_model import WeatherXGBoost
from app.ml.models.adaboost import WeatherAdaBoost
from app.ml.models.dynamic_weighting import DynamicModelWeighter
from app.ml.models.neural_network import WeatherNeuralNetwork

logger = logging.getLogger(__name__)
settings = get_settings()


class MLInferenceEngine:
    """
    High-performance inference engine.
    Orchestrates:
    1. Feature matrix transformation
    2. Base ML models (Random Forest, XGBoost, AdaBoost)
    3. Dynamic model weighting
    4. Two-Head ANN forecast + heteroscedastic uncertainty head
    5. Calibrated confidence scoring
    """

    def __init__(self, artifact_dir: Optional[str] = None):
        self.artifact_dir = Path(artifact_dir or settings.model_artifact_dir)
        self.rf_model: Optional[WeatherRandomForest] = None
        self.xgb_model: Optional[WeatherXGBoost] = None
        self.ada_model: Optional[WeatherAdaBoost] = None
        self.ann: Optional[WeatherNeuralNetwork] = None
        self.scaler = None
        self.feature_names: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.is_loaded = False
        self._load_artifacts()

    def _resolve_artifact_dir(self, city_name: Optional[str] = None) -> Optional[Path]:
        candidate_dirs = []
        # Try city-specific dir first
        if city_name:
            city_slug = city_name.lower().replace(" ", "_")
            for base in [
                self.artifact_dir,
                Path("artifacts"),
                Path("backend/artifacts"),
                Path(__file__).parent.parent.parent.parent / "artifacts",
                Path(__file__).parent.parent.parent.parent / "backend" / "artifacts",
            ]:
                candidate_dirs.append(base / city_slug)
        # Then global root
        candidate_dirs += [
            self.artifact_dir,
            Path("artifacts"),
            Path("backend/artifacts"),
            Path(__file__).parent.parent.parent.parent / "artifacts",
            Path(__file__).parent.parent.parent.parent / "backend" / "artifacts",
        ]
        for c in candidate_dirs:
            if c.exists() and (c / "metadata.json").exists():
                return c
        return None

    def _load_artifacts(self, city_name: Optional[str] = None) -> bool:
        resolved = self._resolve_artifact_dir(city_name)
        if not resolved:
            logger.info("No trained ML model artifacts found. Using dynamic NWP blend mode.")
            return False

        try:
            with open(resolved / "metadata.json") as f:
                self.metadata = json.load(f)

            self.feature_names = joblib.load(resolved / "feature_names.joblib")
            self.scaler = joblib.load(resolved / "scaler.joblib")
            self.rf_model = WeatherRandomForest.load(str(resolved / "random_forest.joblib"))
            self.xgb_model = WeatherXGBoost.load(str(resolved / "xgboost.joblib"))
            self.ada_model = WeatherAdaBoost.load(str(resolved / "adaboost.joblib"))
            self.ann = WeatherNeuralNetwork.load(str(resolved / "neural_network.pt"))

            self.is_loaded = True
            logger.info("ML inference models successfully loaded from %s (city=%s)", resolved, city_name)
            return True
        except Exception as e:
            logger.warning("Failed loading ML artifacts from %s: %s", resolved, e)
            self.is_loaded = False
            return False

    def predict_point(
        self,
        features_dict: Dict[str, float],
        target_var: str = "temperature_c",
    ) -> Tuple[float, float, float]:
        """
        Runs full ML inference for a single time step.
        Returns:
            (prediction, std_uncertainty, confidence_score)
        """
        if not self.is_loaded:
            # Fallback if models not trained
            val = features_dict.get(f"nwp_mean_{target_var}", features_dict.get(f"nwp_gfs_{target_var}", 25.0))
            return float(val), 1.5, 0.75

        # Align features with training feature vector
        vec = np.zeros((1, len(self.feature_names)), dtype=np.float32)
        for i, fname in enumerate(self.feature_names):
            vec[0, i] = features_dict.get(fname, 0.0)

        # Scale features using training scaler
        scaled_vec = self.scaler.transform(vec)

        # Base model predictions (Random Forest, XGBoost, AdaBoost)
        rf_res = float(self.rf_model.predict(scaled_vec)[0])
        xgb_res = float(self.xgb_model.predict(scaled_vec)[0])
        ada_res = float(self.ada_model.predict(scaled_vec)[0])

        base_residuals = [p for p in [rf_res, xgb_res, ada_res] if not np.isnan(p)]
        base_consensus_res = float(np.median(base_residuals)) if base_residuals else 0.0

        # Augmented feature vector with base model predictions for Two-Head ANN
        aug_vec = np.column_stack([scaled_vec, [[rf_res, xgb_res, ada_res]]])

        # ANN prediction + heteroscedastic uncertainty
        try:
            ann_preds, ann_stds = self.ann.predict(aug_vec)
            raw_ann_res = float(ann_preds[0, 0])
            raw_std = float(ann_stds[0, 0])

            # If ANN residual output is physically coherent and aligns with base models
            if not np.isnan(raw_ann_res) and abs(raw_ann_res - base_consensus_res) <= 4.0 and raw_std < 15.0:
                # Weighted blend of ANN meta-learner (50%) and robust tree ensemble (50%)
                final_res = float(0.50 * raw_ann_res + 0.25 * xgb_res + 0.25 * rf_res)
                final_std = float(np.clip(raw_std, 0.4, 4.0))
            else:
                # Tree ensemble fallback if ANN variance is high
                final_res = float(0.45 * xgb_res + 0.45 * rf_res + 0.10 * ada_res)
                final_std = 1.2
        except Exception as e:
            logger.warning("ann_inference_fallback: %s", e)
            final_res = base_consensus_res
            final_std = 1.5

        is_residual = self.metadata.get("is_residual_model", True)
        if is_residual:
            nwp_base = features_dict.get(
                f"nwp_mean_{target_var}_v",
                features_dict.get(
                    f"nwp_mean_{target_var}",
                    features_dict.get(
                        f"nwp_gfs_{target_var}_v",
                        features_dict.get(f"nwp_gfs_{target_var}", 25.0)
                    )
                )
            )
            final_pred = float(nwp_base + final_res)
        else:
            final_pred = float(final_res)

        conf_score = self.ann.confidence_score(final_std) if self.ann else 0.85
        return final_pred, final_std, conf_score


_global_ml_engine: Optional[MLInferenceEngine] = None
# Per-city engine cache: city_slug → MLInferenceEngine
_city_ml_engines: Dict[str, MLInferenceEngine] = {}


def get_ml_inference_engine() -> MLInferenceEngine:
    global _global_ml_engine
    if _global_ml_engine is None:
        _global_ml_engine = MLInferenceEngine()
    return _global_ml_engine


def get_city_ml_engine(city_name: Optional[str]) -> MLInferenceEngine:
    """
    Return a city-specific MLInferenceEngine, loading from city subdirectory.
    Falls back to global engine if city-specific artifacts don't exist.
    """
    if not city_name:
        return get_ml_inference_engine()

    city_slug = city_name.lower().replace(" ", "_")
    if city_slug not in _city_ml_engines:
        engine = MLInferenceEngine()
        # Try to load city-specific artifacts
        engine._load_artifacts(city_name)
        if not engine.is_loaded:
            # Fall back to global artifacts
            engine._load_artifacts(None)
        _city_ml_engines[city_slug] = engine
        logger.info("city_ml_engine_ready",
                    city=city_name, loaded=engine.is_loaded)
    return _city_ml_engines[city_slug]
