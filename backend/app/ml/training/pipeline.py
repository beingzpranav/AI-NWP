"""
Full ML training pipeline with chronological time-series split.

LEAKAGE PREVENTION:
- Strictly chronological train/val/test split (no random shuffle).
- Features only use information available at forecast time.
- Scaler fit on training set only, applied to val/test.
- Rolling/lag windows computed before splitting, shift applied to targets.
"""
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import StandardScaler

from app.ml.features.engineer import build_feature_matrix, TARGET_VARIABLES
from app.ml.models.random_forest import WeatherRandomForest
from app.ml.models.xgboost_model import WeatherXGBoost
from app.ml.models.adaboost import WeatherAdaBoost
from app.ml.models.dynamic_weighting import DynamicModelWeighter
from app.ml.models.neural_network import WeatherNeuralNetwork
from app.ml.metrics.evaluation import evaluate_model, AblationStudy
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
# TEST_RATIO = 0.15 (implied)


def chronological_split(
    df: pd.DataFrame,
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Chronological split: train | val | test (no shuffle).
    Preserves temporal order — critical for time-series forecasting.
    """
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return (
        df.iloc[:train_end].copy(),
        df.iloc[train_end:val_end].copy(),
        df.iloc[val_end:].copy(),
    )


class WeatherForecastingPipeline:
    """
    End-to-end training pipeline that produces:
    1. Trained RF, XGBoost, AdaBoost (base models)
    2. Dynamic weighter (trained on validation errors)
    3. Trained neural network (two-head)
    4. Evaluation metrics & ablation results
    """

    def __init__(
        self,
        artifact_dir: str = None,
        horizon_hours: int = 6,
        target_var: str = "temperature_c",
    ):
        self.artifact_dir = Path(artifact_dir or settings.model_artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.horizon_hours = horizon_hours
        self.target_var = target_var

        self.scaler = StandardScaler()
        self.rf_model: Optional[WeatherRandomForest] = None
        self.xgb_model: Optional[WeatherXGBoost] = None
        self.ada_model: Optional[WeatherAdaBoost] = None
        self.weighter = DynamicModelWeighter()
        self.ann: Optional[WeatherNeuralNetwork] = None
        self.feature_names: List[str] = []
        self.is_trained = False
        self.metrics: Dict = {}

    def run(self, df: pd.DataFrame) -> Dict:
        """
        Full pipeline:
        1. Feature engineering
        2. Chronological split
        3. Scale features
        4. Train base models
        5. Evaluate base models
        6. Compute dynamic weights
        7. Train ANN
        8. Run ablation study
        9. Save artifacts
        """
        logger.info("pipeline_start", target=self.target_var, horizon=self.horizon_hours)

        # ── Step 1: Feature engineering ───────────────────────
        X, y, feature_names = build_feature_matrix(
            df,
            target_var=self.target_var,
            horizon_hours=self.horizon_hours,
            fit_mode=True,
        )
        self.feature_names = feature_names

        if len(X) < 50:
            raise ValueError(f"Insufficient training data: {len(X)} rows after feature engineering")

        # ── Step 2: Chronological split ───────────────────────
        combined = X.copy()
        combined["__target__"] = y.values
        train_df, val_df, test_df = chronological_split(combined)

        # Extract helper columns
        nwp_valid_test = test_df["__nwp_valid__"].values if "__nwp_valid__" in test_df.columns else 0.0
        y_raw_test = test_df["__y_raw__"].values if "__y_raw__" in test_df.columns else test_df["__target__"].values

        drop_cols = ["__target__", "__nwp_valid__", "__y_raw__"]
        drop_cols = [c for c in drop_cols if c in train_df.columns]

        X_train = train_df.drop(drop_cols, axis=1).values
        y_train = train_df["__target__"].values  # residuals
        X_val = val_df.drop(drop_cols, axis=1).values
        y_val = val_df["__target__"].values      # residuals
        X_test = test_df.drop(drop_cols, axis=1).values
        y_test_res = test_df["__target__"].values

        # Remove helper columns from feature_names
        self.feature_names = [c for c in X.columns if c not in drop_cols]

        logger.info("pipeline_split",
                    train=len(X_train), val=len(X_val), test=len(X_test))

        # ── Step 3: Scale features (fit on train ONLY) ────────
        # Fill NaNs with column medians (fit on train only — no leakage)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            col_medians = np.nanmedian(X_train, axis=0)
            col_medians = np.nan_to_num(col_medians, nan=0.0)

        for arr in [X_train, X_val, X_test]:
            nan_mask = np.isnan(arr)
            if np.any(nan_mask):
                arr[nan_mask] = np.take(col_medians, np.where(nan_mask)[1])
            np.nan_to_num(arr, copy=False, nan=0.0)

        X_train_sc = self.scaler.fit_transform(X_train)
        X_val_sc = self.scaler.transform(X_val)
        X_test_sc = self.scaler.transform(X_test)

        X_train_sc = np.nan_to_num(X_train_sc, nan=0.0)
        X_val_sc = np.nan_to_num(X_val_sc, nan=0.0)
        X_test_sc = np.nan_to_num(X_test_sc, nan=0.0)

        # ── Step 4: Train base models (on residuals) ───────────
        self.rf_model = WeatherRandomForest()
        self.rf_model.fit(X_train_sc, y_train, self.feature_names)

        self.xgb_model = WeatherXGBoost()
        self.xgb_model.fit(X_train_sc, y_train, X_val_sc, y_val, self.feature_names)

        self.ada_model = WeatherAdaBoost()
        self.ada_model.fit(X_train_sc, y_train, self.feature_names)

        # ── Step 5: Evaluate base models (final = NWP_valid + predicted_residual)
        rf_res_test = self.rf_model.predict(X_test_sc)
        xgb_res_test = self.xgb_model.predict(X_test_sc)
        ada_res_test = self.ada_model.predict(X_test_sc)

        rf_test_preds = nwp_valid_test + rf_res_test
        xgb_test_preds = nwp_valid_test + xgb_res_test
        ada_test_preds = nwp_valid_test + ada_res_test

        metrics = {}
        for name, preds in [("RF", rf_test_preds), ("XGBoost", xgb_test_preds),
                             ("AdaBoost", ada_test_preds)]:
            m = evaluate_model(y_raw_test, preds, name, self.target_var, self.horizon_hours)
            metrics[name] = m.to_dict()
            logger.info("base_model_eval", **m.to_dict())

        # ── Step 6: Ensemble base predictions → meta-features ─
        rf_val_preds = self.rf_model.predict(X_val_sc)
        xgb_val_preds = self.xgb_model.predict(X_val_sc)
        ada_val_preds = self.ada_model.predict(X_val_sc)

        rf_tr_preds = self.rf_model.predict(X_train_sc)
        xgb_tr_preds = self.xgb_model.predict(X_train_sc)
        ada_tr_preds = self.ada_model.predict(X_train_sc)

        # Augment feature matrices with base model predictions
        X_train_aug = np.column_stack([
            X_train_sc, rf_tr_preds, xgb_tr_preds, ada_tr_preds
        ])
        X_val_aug = np.column_stack([
            X_val_sc, rf_val_preds, xgb_val_preds, ada_val_preds
        ])
        X_test_aug = np.column_stack([
            X_test_sc, rf_res_test, xgb_res_test, ada_res_test
        ])

        # ── Step 7: Train two-head ANN ────────────────────────
        y_train_2d = y_train.reshape(-1, 1)
        y_val_2d = y_val.reshape(-1, 1)

        self.ann = WeatherNeuralNetwork(
            input_dim=X_train_aug.shape[1],
            n_targets=1,
            epochs=80,
            patience=12,
            batch_size=128,
        )
        self.ann.fit(
            X_train_aug, y_train_2d,
            X_val_aug, y_val_2d,
            target_names=[self.target_var],
        )

        # ── Step 8: Evaluate ANN ──────────────────────────────
        ann_res_arr, ann_std_arr = self.ann.predict(X_test_aug)
        ann_preds = nwp_valid_test + ann_res_arr.flatten()
        ann_m = evaluate_model(y_raw_test, ann_preds, "ANN", self.target_var, self.horizon_hours)
        metrics["ANN"] = ann_m.to_dict()
        logger.info("ann_eval", **ann_m.to_dict())


        # ── Step 9: Ablation study ────────────────────────────
        # Section 18: Compare NWP only vs NWP+WU vs NWP+ML vs NWP+ML+WU vs NWP+ML+WU+ANN
        #
        # LEAD-TIME ALIGNMENT: row t holds features valid at t, while y_test[t] is the
        # truth valid at t+h. The NWP baseline must therefore be the NWP value valid
        # at t+h (shift(-h)), otherwise it is scored against the wrong hour and looks
        # artificially bad (diurnal phase error), inflating every "improvement" figure.
        h = self.horizon_hours
        tv = self.target_var

        # 1. NWP only (raw uncorrected NWP, valid at the target time t+h)
        nwp_col = next(
            (c for c in (f"nwp_mean_{tv}", f"nwp_gfs_{tv}") if c in test_df.columns), None
        )
        if nwp_col is not None:
            nwp_only = test_df[nwp_col].shift(-h).values
        else:
            logger.warning("ablation_no_nwp_column", target=tv)
            nwp_only = rf_test_preds

        # Reference baselines every forecast product must beat
        # Persistence: truth at issue time t == y at row t-h (rows are contiguous hourly)
        persistence = pd.Series(y_raw_test).shift(h).values
        # Climatology: mean target by hour-of-day of the target time, from TRAIN only
        if "hour" in train_df.columns and "hour" in test_df.columns:
            clim_by_hour = pd.Series(y_train).groupby(
                (train_df["hour"].values + h) % 24
            ).mean()
            climatology = pd.Series((test_df["hour"].values + h) % 24).map(clim_by_hour).values
        else:
            climatology = np.full(len(y_raw_test), np.nan)

        # 2. NWP + Weather Union (NWP corrected by initial WU bias, no ML)
        bias_col = f"bias_gfs_{tv}"
        wu_col = f"wu_{tv}"
        if bias_col in test_df.columns:
            nwp_wu = nwp_only + test_df[bias_col].fillna(0.0).values * 0.4
        elif wu_col in test_df.columns:
            diff = (test_df[wu_col] - nwp_only).fillna(0.0).values
            nwp_wu = nwp_only + diff * 0.4
        else:
            nwp_wu = nwp_only

        # 3. NWP + ML (Base ML model without Weather Union features)
        wu_feature_idx = [
            i for i, f in enumerate(self.feature_names)
            if f.startswith("wu_") or f.startswith("bias_") or "weather_union" in f
        ]
        X_test_no_wu = X_test_sc.copy()
        if wu_feature_idx:
            X_test_no_wu[:, wu_feature_idx] = 0.0
        nwp_ml_res = self.xgb_model.predict(X_test_no_wu)
        nwp_ml_preds = nwp_valid_test + nwp_ml_res

        # 4. NWP + ML + Weather Union (Base ML with WU features)
        nwp_ml_wu_preds = xgb_test_preds

        # 5. NWP + ML + Weather Union + ANN (Full hybrid architecture)
        full_hybrid_preds = ann_preds

        # Score every experiment on the SAME samples (drops first/last h rows lost to
        # shifting) so that MAE values are directly comparable.
        common = ~(np.isnan(nwp_only) | np.isnan(persistence) | np.isnan(y_raw_test))
        wu_has_data = any(
            train_df[c].notna().any() for c in train_df.columns if c.startswith("wu_")
        )

        ablation = AblationStudy()
        for exp_name, preds in [
            ("NWP only", nwp_only),
            ("Persistence", persistence),
            ("Climatology", climatology),
            ("NWP + Weather Union", nwp_wu),
            ("NWP + ML", nwp_ml_preds),
            ("NWP + ML + Weather Union", nwp_ml_wu_preds),
            ("NWP + ML + Weather Union + ANN", full_hybrid_preds),
        ]:
            ablation.add_result(exp_name, evaluate_model(
                y_raw_test[common], np.asarray(preds, dtype=float)[common],
                exp_name, tv, h))

        ablation_rows = ablation.compare(tv, h)

        # Skill vs persistence + honesty notes
        persist_mae = next(
            (r["mae"] for r in ablation_rows if r["experiment"] == "Persistence"), None
        )
        for row in ablation_rows:
            if persist_mae:
                row["skill_vs_persistence_pct"] = round(
                    (1.0 - row["mae"] / persist_mae) * 100.0, 2)
            if "Weather Union" in row["experiment"] and not wu_has_data:
                row["note"] = (
                    "No historical Weather Union data in training; this row is not an "
                    "independent measurement of WU value."
                )
        metrics["ablation"] = ablation_rows
        metrics["evaluation_notes"] = {
            "truth": "ERA5 + METAR station observations",
            "nwp_baseline_alignment": f"NWP valid at t+{h}h",
            "test_samples": int(common.sum()),
            "test_period_hours": int(len(y_raw_test)),
            "weather_union_in_training": bool(wu_has_data),
        }

        # ── Step 10: Save artifacts ───────────────────────────
        self._save_artifacts(metrics)
        self.is_trained = True
        self.metrics = metrics
        logger.info("pipeline_complete", metrics_keys=list(metrics.keys()))
        return metrics

    def _save_artifacts(self, metrics: dict) -> None:
        self.rf_model.save(str(self.artifact_dir / "random_forest.joblib"))
        self.xgb_model.save(str(self.artifact_dir / "xgboost.joblib"))
        self.ada_model.save(str(self.artifact_dir / "adaboost.joblib"))
        self.ann.save(str(self.artifact_dir / "neural_network.pt"))
        joblib.dump(self.scaler, self.artifact_dir / "scaler.joblib")
        joblib.dump(self.feature_names, self.artifact_dir / "feature_names.joblib")

        meta = {
            "trained_at": datetime.now(tz=timezone.utc).isoformat(),
            "target_var": self.target_var,
            "horizon_hours": self.horizon_hours,
            "n_features": len(self.feature_names),
            "metrics": metrics,
        }
        with open(self.artifact_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2, default=str)
        if "ablation" in metrics:
            with open(self.artifact_dir / "ablation_results.json", "w") as f:
                json.dump(metrics["ablation"], f, indent=2, default=str)
        logger.info("artifacts_saved", dir=str(self.artifact_dir))

    @classmethod
    def load_for_inference(cls, artifact_dir: str, horizon_hours: int = 6,
                           target_var: str = "temperature_c") -> "WeatherForecastingPipeline":
        pipeline = cls(artifact_dir, horizon_hours, target_var)
        pipeline.rf_model = WeatherRandomForest.load(
            str(pipeline.artifact_dir / "random_forest.joblib"))
        pipeline.xgb_model = WeatherXGBoost.load(
            str(pipeline.artifact_dir / "xgboost.joblib"))
        pipeline.ada_model = WeatherAdaBoost.load(
            str(pipeline.artifact_dir / "adaboost.joblib"))
        pipeline.ann = WeatherNeuralNetwork.load(
            str(pipeline.artifact_dir / "neural_network.pt"))
        pipeline.scaler = joblib.load(pipeline.artifact_dir / "scaler.joblib")
        pipeline.feature_names = joblib.load(pipeline.artifact_dir / "feature_names.joblib")
        pipeline.is_trained = True
        return pipeline
