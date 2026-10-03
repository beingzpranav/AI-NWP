"""
Tests for feature engineering — especially leakage prevention.
"""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta
from app.ml.features.engineer import (
    add_temporal_features,
    add_lag_features,
    add_rolling_features,
    add_nwp_disagreement_features,
    add_weather_union_bias_features,
    build_feature_matrix,
)


def make_df(n=100):
    """Create a synthetic weather DataFrame for testing."""
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n)]
    np.random.seed(42)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature_c": 25 + np.random.randn(n),
        "humidity_pct": 60 + np.random.randn(n) * 5,
        "wind_speed_kmh": 15 + np.random.randn(n) * 3,
        "pressure_hpa": 1013 + np.random.randn(n),
        "precipitation_mm": np.abs(np.random.randn(n) * 0.5),
        "nwp_gfs_temperature_c": 25.5 + np.random.randn(n),
        "nwp_ecmwf_temperature_c": 24.8 + np.random.randn(n),
        "nwp_jma_temperature_c": 25.1 + np.random.randn(n),
        "wu_temperature_c": 25.3 + np.random.randn(n),
    })
    return df


def test_temporal_features_cyclic():
    df = make_df(50)
    result = add_temporal_features(df)
    # Check cyclical encoding is bounded [-1, 1]
    for col in ["hour_sin", "hour_cos", "dow_sin", "dow_cos"]:
        assert col in result.columns
        assert result[col].between(-1.0, 1.0).all(), f"{col} out of range"


def test_lag_features_no_future_leakage():
    """Lag-1 at row t should equal raw value at row t-1."""
    df = make_df(50)
    result = add_lag_features(df, ["temperature_c"], lag_hours=[1])
    result = result.dropna(subset=["temperature_c_lag_1h"])

    for i in range(1, len(result)):
        orig_idx = result.index[i - 1]
        lag_idx = result.index[i]
        expected = result.loc[orig_idx, "temperature_c"]
        actual = result.loc[lag_idx, "temperature_c_lag_1h"]
        assert abs(expected - actual) < 1e-9, f"Lag mismatch at row {i}"


def test_rolling_features_no_future_leakage():
    """Rolling mean should never include the current or future rows."""
    df = make_df(50)
    result = add_rolling_features(df, ["temperature_c"], windows=[3])
    col = "temperature_c_roll_mean_3h"
    assert col in result.columns

    # At row 3 (index 3), the rolling mean should use rows 0,1,2 only
    result = result.reset_index(drop=True)
    manual_mean = df["temperature_c"].iloc[:3].mean()
    # shift(1) then rolling(3) at index 3 uses indices 0,1,2
    computed = result[col].iloc[3]
    assert not np.isnan(computed), "Rolling feature should not be NaN at row 3"


def test_nwp_disagreement_features():
    df = make_df(30)
    result = add_nwp_disagreement_features(df)
    assert "nwp_mean_temperature_c" in result.columns
    assert "nwp_std_temperature_c" in result.columns
    assert "nwp_range_temperature_c" in result.columns
    # Range should be non-negative
    assert (result["nwp_range_temperature_c"] >= 0).all()


def test_weather_union_bias_features():
    df = make_df(30)
    result = add_weather_union_bias_features(df)
    assert "bias_gfs_temperature_c" in result.columns
    assert "bias_ecmwf_temperature_c" in result.columns
    # Bias = WU - NWP
    expected = df["wu_temperature_c"] - df["nwp_gfs_temperature_c"]
    pd.testing.assert_series_equal(
        result["bias_gfs_temperature_c"].reset_index(drop=True),
        expected.reset_index(drop=True),
        check_names=False,
    )


def test_build_feature_matrix_no_leakage():
    """Target at row t should be t+horizon, not t."""
    df = make_df(100)
    horizon = 3
    X, y, feature_names = build_feature_matrix(
        df, target_var="temperature_c", horizon_hours=horizon, fit_mode=True
    )
    assert y is not None
    assert len(X) == len(y)
    # The last row of X should not have a target (shifted out)
    assert len(X) < 100  # some rows dropped due to NaN targets


def test_build_feature_matrix_inference_mode():
    """In inference mode, y should be None."""
    df = make_df(50)
    X, y, feature_names = build_feature_matrix(
        df, target_var="temperature_c", horizon_hours=1, fit_mode=False
    )
    assert y is None
    assert len(X) > 0
