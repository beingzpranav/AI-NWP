"""
Feature engineering pipeline.

LEAKAGE SAFETY:
- All rolling/lag features use only past observations.
- shift(1) ensures t-1 is minimum, never t+0 for target.
- Rolling windows use closed='left' where applicable.
- Normalization fit is done on training data only.
"""
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)

TARGET_VARIABLES = [
    "temperature_c",
    "humidity_pct",
    "wind_speed_kmh",
    "precipitation_mm",
    "pressure_hpa",
]

LAG_HOURS = [1, 2, 3, 6, 12, 24]
ROLLING_WINDOWS = [3, 6, 12, 24]


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cyclical time encoding for hour, day_of_week, day_of_year, month.
    Uses sin/cos to avoid ordinality issues.
    """
    df = df.copy()
    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must have a 'timestamp' column")

    ts = pd.to_datetime(df["timestamp"], utc=True)

    df["hour"] = ts.dt.hour
    df["day_of_week"] = ts.dt.dayofweek
    df["day_of_year"] = ts.dt.dayofyear
    df["month"] = ts.dt.month

    # Cyclical encoding
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Season (0=DJF, 1=MAM, 2=JJA, 3=SON)
    df["season"] = ((df["month"] % 12) // 3)

    return df


def add_lag_features(
    df: pd.DataFrame, variables: List[str], lag_hours: List[int] = LAG_HOURS
) -> pd.DataFrame:
    """
    Add lag features for given variables.
    Lag 1 = previous time step (leakage-safe for t+1 forecasting).
    Ensure df is sorted by timestamp before calling.
    """
    df = df.copy().sort_values("timestamp")
    for var in variables:
        if var not in df.columns:
            continue
        for lag in lag_hours:
            col_name = f"{var}_lag_{lag}h"
            df[col_name] = df[var].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame, variables: List[str], windows: List[int] = ROLLING_WINDOWS
) -> pd.DataFrame:
    """
    Rolling mean, std, min, max — all shift(1) to prevent leakage.
    """
    df = df.copy().sort_values("timestamp")
    for var in variables:
        if var not in df.columns:
            continue
        for w in windows:
            # shift(1) before rolling ensures current time step is excluded
            shifted = df[var].shift(1)
            df[f"{var}_roll_mean_{w}h"] = shifted.rolling(w, min_periods=1).mean()
            df[f"{var}_roll_std_{w}h"] = shifted.rolling(w, min_periods=1).std()
            df[f"{var}_roll_min_{w}h"] = shifted.rolling(w, min_periods=1).min()
            df[f"{var}_roll_max_{w}h"] = shifted.rolling(w, min_periods=1).max()
    return df


def add_nwp_disagreement_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate disagreement between NWP models.
    These are useful features for the ensemble to know when models disagree.
    """
    df = df.copy()
    nwp_models = ["gfs", "ecmwf", "jma"]

    for var in ["temperature_c", "humidity_pct", "wind_speed_kmh",
                "precipitation_mm", "pressure_hpa"]:
        cols = [f"nwp_{m}_{var}" for m in nwp_models]
        available = [c for c in cols if c in df.columns]

        if len(available) >= 2:
            df[f"nwp_mean_{var}"] = df[available].mean(axis=1)
            df[f"nwp_std_{var}"] = df[available].std(axis=1)
            df[f"nwp_range_{var}"] = df[available].max(axis=1) - df[available].min(axis=1)

        if len(available) == 3:
            df[f"nwp_gfs_ecmwf_diff_{var}"] = (
                df.get(f"nwp_gfs_{var}", np.nan) - df.get(f"nwp_ecmwf_{var}", np.nan)
            )
            df[f"nwp_gfs_jma_diff_{var}"] = (
                df.get(f"nwp_gfs_{var}", np.nan) - df.get(f"nwp_jma_{var}", np.nan)
            )
            df[f"nwp_ecmwf_jma_diff_{var}"] = (
                df.get(f"nwp_ecmwf_{var}", np.nan) - df.get(f"nwp_jma_{var}", np.nan)
            )

    return df


def add_weather_union_bias_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate bias between Weather Union observations and each NWP model.
    These allow the ML models to learn NWP systematic errors.

    Only uses Weather Union observation from t (current), never t+horizon.
    The observation at t is a valid input when forecasting t+h.
    """
    df = df.copy()

    for var in ["temperature_c", "humidity_pct", "wind_speed_kmh", "pressure_hpa"]:
        wu_col = f"wu_{var}"
        if wu_col not in df.columns:
            continue

        for model in ["gfs", "ecmwf", "jma"]:
            nwp_col = f"nwp_{model}_{var}"
            if nwp_col in df.columns:
                # bias = WU_observation - NWP_forecast (positive = NWP underestimates)
                df[f"bias_{model}_{var}"] = df[wu_col] - df[nwp_col]

    return df


def add_source_availability_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Binary flags indicating data source availability."""
    df = df.copy()
    for model in ["gfs", "ecmwf", "jma"]:
        col = f"nwp_{model}_temperature_c"
    df["weather_union_available"] = (
        (~df["wu_temperature_c"].isna()).astype(int)
        if "wu_temperature_c" in df.columns else 0
    )
    return df


def add_valid_time_and_error_features(
    df: pd.DataFrame, horizon_hours: int = 6
) -> pd.DataFrame:
    """
    Add MOS valid-time NWP predictors and issue-time recent observation error features.
    
    1. Valid-time NWP values valid at t+H (shifted -H)
    2. NWP tendency (difference between valid-time NWP and issue-time NWP)
    3. Issue-time observation error (obs_t - nwp_t) and rolling averages
    4. Valid-time cyclical time encodings
    """
    df = df.copy().sort_values("timestamp")
    nwp_models = ["gfs", "ecmwf", "jma"]
    obs_vars = ["temperature_c", "humidity_pct", "wind_speed_kmh", "precipitation_mm", "pressure_hpa"]

    for var in obs_vars:
        # Issue-time observation feature explicitly captured
        if var in df.columns:
            df[f"obs_{var}_t"] = df[var]

        # Shifted NWP predictions valid at t+H
        for m in nwp_models:
            col = f"nwp_{m}_{var}"
            if col in df.columns:
                df[f"{col}_v"] = df[col].shift(-horizon_hours)

        mean_col = f"nwp_mean_{var}"
        if mean_col in df.columns:
            df[f"{mean_col}_v"] = df[mean_col].shift(-horizon_hours)
            if mean_col in df.columns:
                df[f"nwp_delta_{var}"] = df[f"{mean_col}_v"] - df[mean_col]

        # Recent NWP observation error at issue time t
        if var in df.columns and mean_col in df.columns:
            err = df[var] - df[mean_col]
            df[f"nwp_err_{var}_t"] = err
            shifted_err = err.shift(1)
            df[f"nwp_err_{var}_roll_mean_6h"] = shifted_err.rolling(6, min_periods=1).mean()
            df[f"nwp_err_{var}_roll_mean_24h"] = shifted_err.rolling(24, min_periods=1).mean()

    # Valid-time temporal encodings (for forecast target time t+H)
    ts = pd.to_datetime(df["timestamp"], utc=True)
    valid_ts = ts + pd.Timedelta(hours=horizon_hours)
    df["valid_hour_sin"] = np.sin(2 * np.pi * valid_ts.dt.hour / 24)
    df["valid_hour_cos"] = np.cos(2 * np.pi * valid_ts.dt.hour / 24)
    df["valid_doy_sin"] = np.sin(2 * np.pi * valid_ts.dt.dayofyear / 365)
    df["valid_doy_cos"] = np.cos(2 * np.pi * valid_ts.dt.dayofyear / 365)

    return df


def build_feature_matrix(
    df: pd.DataFrame,
    target_var: str = "temperature_c",
    horizon_hours: int = 1,
    fit_mode: bool = True,
    predict_residual: bool = True,
) -> Tuple[pd.DataFrame, Optional[pd.Series], List[str]]:
    """
    Full feature engineering pipeline with MOS residual learning support.

    Args:
        df: Raw merged DataFrame with all data sources aligned on 'timestamp'
        target_var: Target variable to predict
        horizon_hours: How many hours ahead to forecast
        fit_mode: If True, targets are computed and rows filtered
        predict_residual: If True, target y is the residual error (y_raw - nwp_valid_mean)

    Returns:
        X: Feature DataFrame (with __nwp_valid__ and __y_raw__ metadata columns if fit_mode)
        y: Target Series (residuals if predict_residual=True, else raw targets)
        feature_names: list of feature column names
    """
    df = df.copy().sort_values("timestamp").reset_index(drop=True)

    # ── 1. Temporal features ──────────────────────────────────
    df = add_temporal_features(df)

    # ── 2. Valid-time NWP & recent error features ─────────────
    df = add_valid_time_and_error_features(df, horizon_hours=horizon_hours)

    # ── 3. Lag features (observation variables) ───────────────
    obs_vars = ["temperature_c", "humidity_pct", "wind_speed_kmh",
                "precipitation_mm", "pressure_hpa"]
    obs_vars_available = [v for v in obs_vars if v in df.columns]
    df = add_lag_features(df, obs_vars_available)

    # ── 4. Rolling features ───────────────────────────────────
    df = add_rolling_features(df, obs_vars_available)

    # ── 5. NWP disagreement ───────────────────────────────────
    df = add_nwp_disagreement_features(df)

    # ── 6. Weather Union bias features ───────────────────────
    df = add_weather_union_bias_features(df)

    # ── 7. Source availability flags ─────────────────────────
    df = add_source_availability_flags(df)

    # ── 8. Build target (LEAKAGE-SAFE MOS Residual) ───────────
    y = None
    if fit_mode and target_var in df.columns:
        # Ground truth valid at t+H
        y_raw = df[target_var].shift(-horizon_hours)

        # Baseline NWP valid at t+H
        nwp_valid_col = f"nwp_mean_{target_var}_v"
        if nwp_valid_col not in df.columns:
            nwp_valid_col = f"nwp_gfs_{target_var}_v"
        if nwp_valid_col not in df.columns:
            nwp_valid_col = f"nwp_mean_{target_var}"
        nwp_valid_mean = df[nwp_valid_col] if nwp_valid_col in df.columns else df[target_var]

        if predict_residual:
            y = y_raw - nwp_valid_mean
        else:
            y = y_raw

        # Save metadata helper columns on df
        df["__nwp_valid__"] = nwp_valid_mean
        df["__y_raw__"] = y_raw

        valid_mask = y_raw.notna() & nwp_valid_mean.notna()
        df = df[valid_mask].copy()
        y = y[valid_mask].copy()

    # ── 9. Select feature columns ─────────────────────────────
    exclude = set(obs_vars + ["timestamp", "location_id", "station_id", "__nwp_valid__", "__y_raw__"])
    feature_cols = [
        c for c in df.columns
        if c not in exclude and df[c].dtype in [np.float64, np.float32, np.int64, np.int32]
    ]

    X = df[feature_cols].copy()

    if "__nwp_valid__" in df.columns:
        X["__nwp_valid__"] = df["__nwp_valid__"].values
    if "__y_raw__" in df.columns:
        X["__y_raw__"] = df["__y_raw__"].values

    # Fill remaining NaN with column medians (computed on training set)
    median_cols = [c for c in X.columns if not c.startswith("__")]
    X[median_cols] = X[median_cols].fillna(X[median_cols].median(numeric_only=True))

    logger.info(
        "features_built",
        n_features=len(feature_cols),
        n_rows=len(X),
        target=target_var,
        horizon_hours=horizon_hours,
        fit_mode=fit_mode,
        predict_residual=predict_residual,
    )

    return X, y, feature_cols
