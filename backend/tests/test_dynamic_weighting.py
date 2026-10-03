"""Tests for dynamic model weighting."""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timezone, timedelta
from app.ml.models.dynamic_weighting import DynamicModelWeighter, compute_mae, compute_rmse


def make_error_df(n=50):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n)]
    np.random.seed(0)
    actual = 25 + np.random.randn(n)
    df = pd.DataFrame({
        "timestamp": timestamps,
        "actual_temperature_c": actual,
        # GFS: slightly high bias
        "gfs_temperature_c_pred": actual + 0.5 + np.random.randn(n) * 0.3,
        # ECMWF: accurate
        "ecmwf_temperature_c_pred": actual + 0.1 + np.random.randn(n) * 0.2,
        # JMA: large error
        "jma_temperature_c_pred": actual + 1.5 + np.random.randn(n) * 0.5,
    })
    return df


def test_weights_sum_to_one():
    weighter = DynamicModelWeighter()
    df = make_error_df()
    weights = weighter.compute_weights(df, variable="temperature_c",
                                       available_models=["GFS", "ECMWF", "JMA"])
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}, expected 1.0"


def test_ecmwf_higher_weight_when_more_accurate():
    """ECMWF has smallest error in make_error_df, should get highest weight."""
    weighter = DynamicModelWeighter()
    df = make_error_df(n=100)
    weights = weighter.compute_weights(df, variable="temperature_c",
                                       available_models=["GFS", "ECMWF", "JMA"])
    assert weights["ECMWF"] > weights["GFS"], "ECMWF should outweigh GFS"
    assert weights["ECMWF"] > weights["JMA"], "ECMWF should outweigh JMA"


def test_weights_min_floor():
    """Every model should get at least min_weight even if poor performer."""
    weighter = DynamicModelWeighter(min_weight=0.05)
    df = make_error_df()
    weights = weighter.compute_weights(df, variable="temperature_c",
                                       available_models=["GFS", "ECMWF", "JMA"])
    for model, w in weights.items():
        assert w >= 0.04, f"{model} weight {w} below min floor"


def test_blend_predictions():
    preds = {"GFS": 31.8, "ECMWF": 32.4, "JMA": 31.5}
    weights = {"GFS": 0.30, "ECMWF": 0.40, "JMA": 0.30}
    blended = DynamicModelWeighter.blend_predictions(preds, weights)
    expected = 31.8 * 0.30 + 32.4 * 0.40 + 31.5 * 0.30
    assert abs(blended - expected) < 1e-6


def test_blend_with_missing_model():
    preds = {"GFS": 31.8, "ECMWF": None, "JMA": 31.5}
    weights = {"GFS": 0.40, "ECMWF": 0.40, "JMA": 0.20}
    blended = DynamicModelWeighter.blend_predictions(preds, weights)
    # Only GFS and JMA contribute
    assert not np.isnan(blended)
    assert 31.5 <= blended <= 31.9


def test_fallback_when_insufficient_data():
    weighter = DynamicModelWeighter()
    df = pd.DataFrame({"timestamp": [], "actual_temperature_c": []})
    weights = weighter.compute_weights(df, variable="temperature_c")
    assert abs(sum(weights.values()) - 1.0) < 1e-6
