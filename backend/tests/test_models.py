"""
ML model unit tests.
Tests RF, XGBoost, AdaBoost, ANN, and dynamic weighting.
"""
import numpy as np
import pytest
from sklearn.datasets import make_regression


def make_data(n=300, n_features=20):
    X, y = make_regression(
        n_samples=n, n_features=n_features,
        noise=0.5, random_state=42
    )
    return X.astype(np.float32), y.astype(np.float32)


# ── Random Forest ─────────────────────────────────────────────
def test_random_forest_fit_predict():
    from app.ml.models.random_forest import WeatherRandomForest
    X, y = make_data()
    model = WeatherRandomForest(n_estimators=20)
    model.fit(X, y)
    assert model.is_fitted
    preds = model.predict(X[:10])
    assert len(preds) == 10
    assert not np.any(np.isnan(preds))


def test_random_forest_feature_importance():
    from app.ml.models.random_forest import WeatherRandomForest
    X, y = make_data()
    features = [f"feat_{i}" for i in range(X.shape[1])]
    model = WeatherRandomForest(n_estimators=10)
    model.fit(X, y, features)
    imp = model.feature_importances()
    assert len(imp) == X.shape[1]
    assert abs(sum(imp.values()) - 1.0) < 1e-5


# ── XGBoost ───────────────────────────────────────────────────
def test_xgboost_fit_predict():
    from app.ml.models.xgboost_model import WeatherXGBoost
    X, y = make_data()
    split = int(len(X) * 0.8)
    model = WeatherXGBoost(n_estimators=50)
    model.fit(X[:split], y[:split], X[split:], y[split:])
    assert model.is_fitted
    preds = model.predict(X[:10])
    assert len(preds) == 10
    assert not np.any(np.isnan(preds))


# ── AdaBoost ──────────────────────────────────────────────────
def test_adaboost_fit_predict():
    from app.ml.models.adaboost import WeatherAdaBoost
    X, y = make_data()
    model = WeatherAdaBoost(n_estimators=30)
    model.fit(X, y)
    assert model.is_fitted
    preds = model.predict(X[:10])
    assert len(preds) == 10
    assert not np.any(np.isnan(preds))


# ── Neural Network ────────────────────────────────────────────
def test_ann_fit_predict():
    from app.ml.models.neural_network import WeatherNeuralNetwork
    X, y = make_data(n=200, n_features=15)
    y = y.reshape(-1, 1)
    split = int(len(X) * 0.8)

    ann = WeatherNeuralNetwork(
        input_dim=15, n_targets=1,
        epochs=5, patience=3, batch_size=32
    )
    ann.fit(X[:split], y[:split], X[split:], y[split:], target_names=["temperature_c"])
    assert ann.is_fitted

    preds, stds = ann.predict(X[:5])
    assert preds.shape == (5, 1)
    assert stds.shape == (5, 1)
    # Std should be non-negative
    assert np.all(stds >= 0)


def test_ann_confidence_score():
    from app.ml.models.neural_network import WeatherNeuralNetwork
    ann = WeatherNeuralNetwork(input_dim=5, n_targets=1, epochs=2, patience=2)
    X, y = make_data(n=50, n_features=5)
    y = y.reshape(-1, 1)
    ann.fit(X[:40], y[:40], X[40:], y[40:])
    _, stds = ann.predict(X[:3])
    score = ann.confidence_score(stds)
    assert 0.0 <= score <= 1.0


def test_ann_two_heads_produce_different_outputs():
    from app.ml.models.neural_network import WeatherNeuralNetwork
    import torch
    ann = WeatherNeuralNetwork(input_dim=10, n_targets=2, epochs=3, patience=2)
    X, _ = make_data(n=60, n_features=10)
    y = np.random.randn(60, 2).astype(np.float32)
    ann.fit(X[:50], y[:50], X[50:], y[50:])
    preds, stds = ann.predict(X[:5])
    # HEAD 1 (forecast) and HEAD 2 (uncertainty) should differ
    assert not np.allclose(preds, stds)


# ── Dynamic Weighting ─────────────────────────────────────────
def test_dynamic_weighting_weights_sum_to_one():
    from app.ml.models.dynamic_weighting import DynamicModelWeighter
    import pandas as pd
    from datetime import datetime, timezone, timedelta

    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    n = 72
    actual = 25 + np.random.randn(n)
    df = pd.DataFrame({
        "timestamp":              [base + timedelta(hours=i) for i in range(n)],
        "actual_temperature_c":   actual,
        "gfs_temperature_c_pred": actual + 0.5 + np.random.randn(n) * 0.3,
        "ecmwf_temperature_c_pred": actual + 0.1 + np.random.randn(n) * 0.2,
        "jma_temperature_c_pred": actual + 1.0 + np.random.randn(n) * 0.5,
    })
    weighter = DynamicModelWeighter()
    weights = weighter.compute_weights(
        df, variable="temperature_c",
        available_models=["GFS", "ECMWF", "JMA"]
    )
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-6
    # Each weight >= min_weight floor
    for w in weights.values():
        assert w >= 0.04


def test_dynamic_weighting_low_error_gets_high_weight():
    from app.ml.models.dynamic_weighting import DynamicModelWeighter
    import pandas as pd
    from datetime import datetime, timezone, timedelta

    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    n = 100
    actual = 25 + np.random.randn(n)
    df = pd.DataFrame({
        "timestamp":                [base + timedelta(hours=i) for i in range(n)],
        "actual_temperature_c":     actual,
        "gfs_temperature_c_pred":   actual + 2.0 + np.random.randn(n),  # worst
        "ecmwf_temperature_c_pred": actual + 0.05 + np.random.randn(n) * 0.1,  # best
        "jma_temperature_c_pred":   actual + 1.0 + np.random.randn(n) * 0.5,
    })
    weighter = DynamicModelWeighter()
    weights = weighter.compute_weights(
        df, variable="temperature_c",
        available_models=["GFS", "ECMWF", "JMA"]
    )
    assert weights["ECMWF"] > weights["GFS"], "Low-error ECMWF should outweigh high-error GFS"


def test_blend_predictions():
    from app.ml.models.dynamic_weighting import DynamicModelWeighter
    preds   = {"GFS": 30.0, "ECMWF": 32.0, "JMA": 31.0}
    weights = {"GFS": 0.25, "ECMWF": 0.50, "JMA": 0.25}
    result = DynamicModelWeighter.blend_predictions(preds, weights)
    expected = 30.0 * 0.25 + 32.0 * 0.50 + 31.0 * 0.25
    assert abs(result - expected) < 1e-5


def test_blend_handles_none_predictions():
    from app.ml.models.dynamic_weighting import DynamicModelWeighter
    preds   = {"GFS": 30.0, "ECMWF": None, "JMA": 31.0}
    weights = {"GFS": 0.33, "ECMWF": 0.34, "JMA": 0.33}
    result = DynamicModelWeighter.blend_predictions(preds, weights)
    assert not np.isnan(result)
    assert 30.0 <= result <= 31.0
