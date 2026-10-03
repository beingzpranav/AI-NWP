"""
Comprehensive tests for Ablation Testing Framework and Pipeline.
Validates:
- 5-stage ablation comparison (Section 18)
- Leakage prevention (Section 4)
- Absolute & percentage improvement calculation
- Weather Union error correction impact
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

# Add root and backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.ml.metrics.evaluation import AblationStudy, evaluate_model, ModelMetrics
from app.ml.training.pipeline import WeatherForecastingPipeline, chronological_split
from ml.data import generate_synthetic_weather_dataset


def test_ablation_study_five_stages():
    """Verify Section 18: compare all 5 stages with baseline error, absolute and pct improvements."""
    ablation = AblationStudy()
    
    # 1. Baseline NWP
    m_nwp = ModelMetrics(
        model_name="NWP only", variable="temperature_c", horizon_hours=6,
        mae=1.50, rmse=1.90, r2=0.70, mape=5.5, sample_count=100
    )
    # 2. NWP + WU
    m_wu = ModelMetrics(
        model_name="NWP + Weather Union", variable="temperature_c", horizon_hours=6,
        mae=1.30, rmse=1.65, r2=0.78, mape=4.8, sample_count=100
    )
    # 3. NWP + ML
    m_ml = ModelMetrics(
        model_name="NWP + ML", variable="temperature_c", horizon_hours=6,
        mae=1.05, rmse=1.35, r2=0.85, mape=4.0, sample_count=100
    )
    # 4. NWP + ML + WU
    m_ml_wu = ModelMetrics(
        model_name="NWP + ML + Weather Union", variable="temperature_c", horizon_hours=6,
        mae=0.82, rmse=1.05, r2=0.91, mape=3.1, sample_count=100
    )
    # 5. Full Hybrid ANN
    m_ann = ModelMetrics(
        model_name="NWP + ML + Weather Union + ANN", variable="temperature_c", horizon_hours=6,
        mae=0.69, rmse=0.89, r2=0.94, mape=2.6, sample_count=100
    )

    ablation.add_result("NWP only", m_nwp)
    ablation.add_result("NWP + Weather Union", m_wu)
    ablation.add_result("NWP + ML", m_ml)
    ablation.add_result("NWP + ML + Weather Union", m_ml_wu)
    ablation.add_result("NWP + ML + Weather Union + ANN", m_ann)

    comparison = ablation.compare("temperature_c", 6)
    assert len(comparison) == 5

    exp_map = {c["experiment"]: c for c in comparison}
    assert "NWP only" in exp_map
    assert "NWP + Weather Union" in exp_map
    assert "NWP + ML" in exp_map
    assert "NWP + ML + Weather Union" in exp_map
    assert "NWP + ML + Weather Union + ANN" in exp_map

    # Check baseline error and improvements
    base_c = exp_map["NWP only"]
    assert base_c["baseline_error"] == 1.50
    assert base_c["absolute_improvement"] == 0.0
    assert base_c["percentage_improvement"] == 0.0

    wu_c = exp_map["NWP + Weather Union"]
    assert wu_c["baseline_error"] == 1.50
    assert wu_c["new_error"] == 1.30
    assert abs(wu_c["absolute_improvement"] - 0.20) < 1e-4
    assert abs(wu_c["percentage_improvement"] - 13.33) < 0.1

    hybrid_c = exp_map["NWP + ML + Weather Union + ANN"]
    assert hybrid_c["new_error"] == 0.69
    assert hybrid_c["absolute_improvement"] > 0.8
    assert hybrid_c["percentage_improvement"] > 50.0


def test_leakage_safety_chronological_split():
    """Verify chronological split has zero overlap and preserves strict time-ordering."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=100, freq="h"),
        "val": range(100)
    })
    train, val, test = chronological_split(df, train_ratio=0.7, val_ratio=0.15)
    
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15

    # Strict chronological ordering
    assert train["timestamp"].max() < val["timestamp"].min()
    assert val["timestamp"].max() < test["timestamp"].min()


def test_pipeline_ablation_run(tmp_path):
    """Test running full pipeline on synthetic dataset to ensure ablation produces real metrics."""
    df = generate_synthetic_weather_dataset(n_hours=120)
    pipeline = WeatherForecastingPipeline(
        artifact_dir=str(tmp_path),
        horizon_hours=2,
        target_var="temperature_c"
    )
    metrics = pipeline.run(df)
    assert "ablation" in metrics
    assert len(metrics["ablation"]) == 5
    for row in metrics["ablation"]:
        assert "experiment" in row
        assert "mae" in row
        assert "baseline_error" in row
        assert "new_error" in row
        assert "absolute_improvement" in row
        assert "percentage_improvement" in row
