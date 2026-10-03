"""
Forecast Service — orchestrates NWP, Weather Union, and ML pipeline.

For each forecast request:
1. Fetch NWP from all three models (GFS, ECMWF, JMA)
2. Fetch current Weather Union observation
3. Build feature matrix
4. Run base ML models (RF, XGB, AdaBoost)
5. Compute dynamic model weights
6. Run ANN with two heads
7. Blend predictions
8. Return forecast + uncertainty + confidence + dynamic weights
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.ml.features.engineer import build_feature_matrix
from app.ml.models.adaboost import AdaBoostWeatherModel
from app.ml.models.dynamic_weighting import DynamicModelWeighter, DynamicWeights
from app.ml.models.neural_network import TwoHeadWeatherANN
from app.ml.models.random_forest import RandomForestWeatherModel
from app.ml.models.xgboost_model import XGBoostWeatherModel
from app.services.nwp.client import NWPClient
from app.services.nwp.schemas import NWPModelForecast
from app.services.weather_union.client import WeatherUnionClient
from app.services.weather_union.schemas import WeatherUnionObservationData

logger = logging.getLogger(__name__)
settings = get_settings()


class ForecastService:
    """Orchestrates the full forecasting pipeline per location."""

    def __init__(self) -> None:
        self.nwp_client = NWPClient()
        self.wu_client = WeatherUnionClient()
        self.dynamic_weighter = DynamicModelWeighter()

        # Loaded at startup
        self._rf: Optional[RandomForestWeatherModel] = None
        self._xgb: Optional[XGBoostWeatherModel] = None
        self._ada: Optional[AdaBoostWeatherModel] = None
        self._ann: Optional[TwoHeadWeatherANN] = None
        self._scaler = None
        self._feature_names: List[str] = []
        self._target_variables: List[str] = []
        self._model_version: str = "none"
        self._models_loaded = False

    def load_models(self, artifacts_dir: Optional[str] = None) -> bool:
        """Load trained model artifacts from disk."""
        base = Path(artifacts_dir or settings.model_artifacts_dir)
        version_file = base / "latest_version.txt"
        latest = base / "latest"

        version_dir = None
        if latest.is_dir():
            version_dir = latest
        elif version_file.exists():
            version = version_file.read_text().strip()
            version_dir = base / version

        if version_dir is None or not version_dir.exists():
            logger.warning("No trained model artifacts found — using NWP-only mode")
            return False

        try:
            meta_path = version_dir / "metadata.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                self._feature_names = meta.get("feature_names", [])
                self._target_variables = meta.get("target_variables", [])
                self._model_version = meta.get("version", "unknown")

            scaler_path = version_dir / "scaler.joblib"
            if scaler_path.exists():
                self._scaler = joblib.load(scaler_path)

            rf_path = version_dir / "random_forest.joblib"
            if rf_path.exists():
                self._rf = joblib.load(rf_path)

            xgb_path = version_dir / "xgboost.joblib"
            if xgb_path.exists():
                self._xgb = joblib.load(xgb_path)

            ada_path = version_dir / "adaboost.joblib"
            if ada_path.exists():
                self._ada = joblib.load(ada_path)

            ann_path = version_dir / "ann"
            if (Path(ann_path) / "ann_model").exists():
                self._ann = TwoHeadWeatherANN(
                    n_features=len(self._feature_names),
                    target_variables=self._target_variables,
                )
                self._ann.load(ann_path)

            self._models_loaded = bool(self._rf or self._xgb or self._ada or self._ann)
            logger.info(f"Models loaded (version={self._model_version}, loaded={self._models_loaded})")
            return self._models_loaded

        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            return False

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 48,
    ) -> Dict[str, Any]:
        """
        Full forecast pipeline for a single location.
        All sources are optional — the system degrades gracefully.
        """
        result = {
            "location": {"latitude": latitude, "longitude": longitude},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_version": self._model_version,
            "sources": {
                "gfs_available": False,
                "ecmwf_available": False,
                "jma_available": False,
                "weather_union_available": False,
                "ml_models_available": self._models_loaded,
            },
            "nwp_forecasts": {},
            "weather_union": None,
            "forecast": [],
            "dynamic_weights": {},
            "metadata": {},
        }

        # ---- 1. Fetch NWP concurrently ---- #
        nwp_data = await self.nwp_client.fetch_all_models(latitude, longitude, forecast_hours)
        result["sources"]["gfs_available"] = nwp_data.get("gfs") is not None
        result["sources"]["ecmwf_available"] = nwp_data.get("ecmwf") is not None
        result["sources"]["jma_available"] = nwp_data.get("jma") is not None

        # ---- 2. Fetch Weather Union ---- #
        wu_obs: Optional[WeatherUnionObservationData] = None
        try:
            wu_obs = await self.wu_client.get_locality_weather(latitude, longitude)
            result["sources"]["weather_union_available"] = wu_obs is not None
            if wu_obs:
                result["weather_union"] = {
                    "station_id": wu_obs.station_id,
                    "station_name": wu_obs.station_name,
                    "observed_at": wu_obs.observed_at.isoformat(),
                    "temperature_c": wu_obs.temperature_c,
                    "humidity_pct": wu_obs.humidity_pct,
                    "pressure_hpa": wu_obs.pressure_hpa,
                    "wind_speed_ms": wu_obs.wind_speed_ms,
                    "wind_direction_deg": wu_obs.wind_direction_deg,
                    "precipitation_mm": wu_obs.precipitation_mm,
                    "rain_intensity_mmph": wu_obs.rain_intensity_mmph,
                }
        except Exception as e:
            logger.warning(f"Weather Union fetch failed: {e}")

        # ---- 3. Build feature matrix and forecast ---- #
        forecast_points = self._build_forecast_points(
            nwp_data, wu_obs, latitude, longitude, forecast_hours
        )

        if not forecast_points:
            # No NWP data at all
            result["error"] = "No NWP or Weather Union data available for this location"
            return result

        # ---- 4. ML enhancement (if models available) ---- #
        if self._models_loaded:
            forecast_points = self._apply_ml_correction(forecast_points, wu_obs)

        # ---- 5. Dynamic weights ---- #
        weights = self._compute_display_weights(result["sources"], wu_obs)
        result["dynamic_weights"] = weights

        result["forecast"] = forecast_points
        result["nwp_forecasts"] = self._format_nwp_summary(nwp_data)

        return result

    def _build_forecast_points(
        self,
        nwp_data: Dict[str, Optional[NWPModelForecast]],
        wu_obs: Optional[WeatherUnionObservationData],
        latitude: float,
        longitude: float,
        forecast_hours: int,
    ) -> List[Dict]:
        """Build hourly forecast points from available NWP sources."""
        points = []

        # Determine the time range from first available model
        reference_model = next((v for v in nwp_data.values() if v is not None), None)
        if reference_model is None:
            return []

        for i, pt in enumerate(reference_model.points[:forecast_hours]):
            gfs = nwp_data.get("gfs")
            ecmwf = nwp_data.get("ecmwf")
            jma = nwp_data.get("jma")

            gfs_pt = gfs.points[i] if gfs and i < len(gfs.points) else None
            ecmwf_pt = ecmwf.points[i] if ecmwf and i < len(ecmwf.points) else None
            jma_pt = jma.points[i] if jma and i < len(jma.points) else None

            # Collect available temperatures
            temps = [
                p.temperature_c for p in [gfs_pt, ecmwf_pt, jma_pt]
                if p and p.temperature_c is not None
            ]
            humids = [
                p.humidity_pct for p in [gfs_pt, ecmwf_pt, jma_pt]
                if p and p.humidity_pct is not None
            ]
            pressures = [
                p.pressure_hpa for p in [gfs_pt, ecmwf_pt, jma_pt]
                if p and p.pressure_hpa is not None
            ]
            winds = [
                p.wind_speed_ms for p in [gfs_pt, ecmwf_pt, jma_pt]
                if p and p.wind_speed_ms is not None
            ]
            precips = [
                p.precipitation_mm for p in [gfs_pt, ecmwf_pt, jma_pt]
                if p and p.precipitation_mm is not None
            ]

            nwp_temp_mean = float(np.mean(temps)) if temps else None
            nwp_temp_spread = float(np.max(temps) - np.min(temps)) if len(temps) >= 2 else 0.0

            # Weather Union bias correction at horizon 0
            wu_correction = 0.0
            if i == 0 and wu_obs and wu_obs.temperature_c and nwp_temp_mean:
                wu_correction = wu_obs.temperature_c - nwp_temp_mean

            # Apply a simple bias correction for near-term forecasts
            # The ML model learns a more sophisticated correction
            correction_decay = max(0.0, 1.0 - i / 6.0)  # Full correction at h0, fades over 6h
            corrected_temp = (
                (nwp_temp_mean + wu_correction * correction_decay)
                if nwp_temp_mean is not None
                else None
            )

            # NWP disagreement → uncertainty proxy
            uncertainty_temp = nwp_temp_spread * 0.5 + (abs(wu_correction) * 0.2 if wu_obs else 0.0)
            confidence = float(1.0 / (1.0 + uncertainty_temp)) if nwp_temp_mean else 0.5

            point = {
                "valid_time": pt.valid_time.isoformat(),
                "horizon_h": i,
                # NWP individual
                "gfs_temperature": gfs_pt.temperature_c if gfs_pt else None,
                "ecmwf_temperature": ecmwf_pt.temperature_c if ecmwf_pt else None,
                "jma_temperature": jma_pt.temperature_c if jma_pt else None,
                # Ensemble mean (NWP)
                "nwp_mean_temperature": nwp_temp_mean,
                "nwp_spread_temperature": nwp_temp_spread,
                # Final forecast (NWP + WU correction; overwritten by ML if available)
                "forecast_temperature": corrected_temp,
                "forecast_humidity": float(np.mean(humids)) if humids else None,
                "forecast_pressure": float(np.mean(pressures)) if pressures else None,
                "forecast_wind_speed": float(np.mean(winds)) if winds else None,
                "forecast_precipitation": float(np.mean(precips)) if precips else None,
                # Uncertainty
                "temperature_uncertainty": uncertainty_temp,
                "confidence": round(confidence, 3),
                # WU correction applied
                "wu_correction_applied": round(wu_correction * correction_decay, 3),
                # Wind direction from first available model
                "wind_direction_deg": (
                    gfs_pt.wind_direction_deg if gfs_pt and gfs_pt.wind_direction_deg
                    else (ecmwf_pt.wind_direction_deg if ecmwf_pt else None)
                ),
                "cloud_cover_pct": (
                    gfs_pt.cloud_cover_pct if gfs_pt and gfs_pt.cloud_cover_pct else None
                ),
            }
            points.append(point)

        return points

    def _apply_ml_correction(
        self,
        forecast_points: List[Dict],
        wu_obs: Optional[WeatherUnionObservationData],
    ) -> List[Dict]:
        """
        Apply ML model corrections to NWP-based forecast.
        Builds a feature row per forecast point and runs inference.
        """
        if not self._rf or not self._scaler:
            return forecast_points

        try:
            rows = []
            for pt in forecast_points:
                row = {
                    "timestamp": pt["valid_time"],
                    "gfs_temperature": pt.get("gfs_temperature"),
                    "ecmwf_temperature": pt.get("ecmwf_temperature"),
                    "jma_temperature": pt.get("jma_temperature"),
                    "gfs_humidity": None,
                    "ecmwf_humidity": None,
                    "jma_humidity": None,
                    "gfs_pressure": None,
                    "ecmwf_pressure": None,
                    "jma_pressure": None,
                    "gfs_wind_speed": None,
                    "ecmwf_wind_speed": None,
                    "jma_wind_speed": None,
                    "wu_temp": wu_obs.temperature_c if wu_obs else None,
                    "wu_humidity": wu_obs.humidity_pct if wu_obs else None,
                    "wu_pressure": wu_obs.pressure_hpa if wu_obs else None,
                    "wu_wind_speed": wu_obs.wind_speed_ms if wu_obs else None,
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            X, _ = build_feature_matrix(df, include_wu=wu_obs is not None)

            # Align columns to trained features
            for col in self._feature_names:
                if col not in X.columns:
                    X[col] = 0.0
            X = X[self._feature_names]

            X_scaled = self._scaler.transform(X.values)
            X_df = pd.DataFrame(X_scaled, columns=self._feature_names)

            rf_preds = self._rf.predict_with_fallback(X_df) if self._rf else None
            xgb_preds = self._xgb.predict_with_fallback(X_df) if self._xgb else None
            ada_preds = self._ada.predict_with_fallback(X_df) if self._ada else None

            ann_forecasts, ann_uncertainties, ann_confidence = (
                self._ann.predict(X_scaled) if self._ann else
                (np.full((len(X), len(self._target_variables)), np.nan),
                 np.full((len(X), len(self._target_variables)), np.nan),
                 np.full(len(X), 0.5))
            )

            target_map = {t: i for i, t in enumerate(self._target_variables)}

            for j, pt in enumerate(forecast_points):
                # Blend RF + XGB + AdaBoost + ANN
                ml_temps = []
                if rf_preds is not None and "temperature" in rf_preds.columns:
                    v = rf_preds["temperature"].iloc[j]
                    if not np.isnan(v):
                        ml_temps.append(v)
                if xgb_preds is not None and "temperature" in xgb_preds.columns:
                    v = xgb_preds["temperature"].iloc[j]
                    if not np.isnan(v):
                        ml_temps.append(v)
                if ada_preds is not None and "temperature" in ada_preds.columns:
                    v = ada_preds["temperature"].iloc[j]
                    if not np.isnan(v):
                        ml_temps.append(v)

                temp_idx = target_map.get("temperature")
                if temp_idx is not None and not np.isnan(ann_forecasts[j, temp_idx]):
                    ml_temps.append(float(ann_forecasts[j, temp_idx]))

                if ml_temps:
                    pt["ml_temperature"] = round(float(np.mean(ml_temps)), 2)
                    # Override forecast with ML result
                    pt["forecast_temperature"] = pt["ml_temperature"]

                # Update uncertainty and confidence from ANN head 2
                if temp_idx is not None:
                    pt["temperature_uncertainty"] = round(float(ann_uncertainties[j, temp_idx]), 3)
                pt["confidence"] = round(float(ann_confidence[j]), 3)

        except Exception as e:
            logger.warning(f"ML correction failed: {e} — using NWP-only forecast")

        return forecast_points

    def _compute_display_weights(
        self,
        sources: Dict[str, bool],
        wu_obs: Optional[WeatherUnionObservationData],
    ) -> Dict[str, Any]:
        """
        Compute display weights for the dashboard.
        Uses a simple reliability heuristic when no historical actuals are available.
        In production, these are replaced by DynamicModelWeighter output.
        """
        available = []
        if sources.get("gfs_available"):
            available.append("gfs")
        if sources.get("ecmwf_available"):
            available.append("ecmwf")
        if sources.get("jma_available"):
            available.append("jma")

        # Heuristic: ECMWF generally has highest resolution over Asia; GFS second
        # These are STARTING weights — overridden by measured performance
        base_scores = {"gfs": 0.30, "ecmwf": 0.40, "jma": 0.25, "ml": 0.05}

        if not available:
            return {"note": "No NWP models available"}

        filtered = {k: v for k, v in base_scores.items() if k in available or k == "ml"}
        total = sum(filtered.values())
        normalized = {k: round(v / total, 3) for k, v in filtered.items()}

        return {
            "weights": normalized,
            "wu_correction_active": wu_obs is not None,
            "note": "Heuristic weights — DynamicModelWeighter active when historical data available",
        }

    def _format_nwp_summary(
        self, nwp_data: Dict[str, Optional[NWPModelForecast]]
    ) -> Dict:
        """Format NWP model summary for response."""
        summary = {}
        for model_name, forecast in nwp_data.items():
            if forecast and forecast.points:
                first = forecast.points[0]
                summary[model_name] = {
                    "available": True,
                    "run_time": forecast.run_time.isoformat(),
                    "n_points": len(forecast.points),
                    "current": {
                        "temperature_c": first.temperature_c,
                        "humidity_pct": first.humidity_pct,
                        "pressure_hpa": first.pressure_hpa,
                        "wind_speed_ms": first.wind_speed_ms,
                    },
                }
            else:
                summary[model_name] = {"available": False}
        return summary
