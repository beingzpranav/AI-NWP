#!/usr/bin/env python3
"""
Training script — generates synthetic training data and runs the full pipeline.

In production replace generate_synthetic_data() with a real DB query that fetches:
  - Historical NWP forecasts stored in nwp_forecasts table
  - Historical Weather Union observations from weather_union_observations
  - Ground-truth observations from weather_observations

Usage:
    cd weather-ai-platform
    python scripts/train.py
    python scripts/train.py --target humidity_pct --horizon 12
    python scripts/train.py --target wind_speed_kmh --horizon 3 --data-hours 5000
"""
import argparse
import sys
import os
from pathlib import Path

# Allow backend imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta


def generate_synthetic_data(n_hours: int = 3000) -> pd.DataFrame:
    """
    Generates realistic synthetic hourly weather data.
    Swap this out for real DB queries in production.

    NWP systematic biases are baked in so the ML model has something to correct:
      GFS:   slight high-temperature bias
      ECMWF: most accurate (smallest noise)
      JMA:   largest bias

    Weather Union simulates a localized urban station ~1.2°C warmer than NWP grid.
    WU data has ~15% dropout to simulate real outages.
    """
    np.random.seed(42)
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n_hours)]
    hours = np.array([t.hour for t in timestamps])
    doys  = np.array([t.timetuple().tm_yday for t in timestamps])

    # Diurnal + seasonal base temperature
    temp_diurnal  = 5.0  * np.sin(2 * np.pi * (hours - 6) / 24)
    temp_seasonal = 8.0  * np.sin(2 * np.pi * (doys  - 80) / 365)
    temp_base     = 26.0 + temp_diurnal + temp_seasonal + np.random.randn(n_hours) * 1.2

    # Ground truth
    humidity_base  = np.clip(65 - 0.4 * temp_diurnal + np.random.randn(n_hours) * 4, 15, 100)
    pressure_base  = 1013 + 2 * np.sin(2 * np.pi * doys / 365) + np.random.randn(n_hours) * 0.8
    wind_base      = np.abs(8 + np.random.randn(n_hours) * 3)
    precip_base    = np.where(np.random.random(n_hours) > 0.85,
                              np.abs(np.random.exponential(2.0, n_hours)), 0.0)

    # NWP forecasts with realistic biases
    gfs_temp   = temp_base  + 0.6  + np.random.randn(n_hours) * 0.9
    ecmwf_temp = temp_base  + 0.15 + np.random.randn(n_hours) * 0.5   # most accurate
    jma_temp   = temp_base  + 1.1  + np.random.randn(n_hours) * 1.1   # largest bias

    gfs_hum    = humidity_base  + 2.0 + np.random.randn(n_hours) * 3.0
    ecmwf_hum  = humidity_base  - 0.5 + np.random.randn(n_hours) * 2.0
    jma_hum    = humidity_base  + 1.5 + np.random.randn(n_hours) * 3.5

    gfs_wind   = np.abs(wind_base + np.random.randn(n_hours) * 1.5)
    ecmwf_wind = np.abs(wind_base + np.random.randn(n_hours) * 1.0)
    jma_wind   = np.abs(wind_base + np.random.randn(n_hours) * 2.0)

    gfs_pres   = pressure_base + 0.2 + np.random.randn(n_hours) * 0.5
    ecmwf_pres = pressure_base - 0.1 + np.random.randn(n_hours) * 0.3
    jma_pres   = pressure_base + 0.3 + np.random.randn(n_hours) * 0.6

    # Weather Union: urban station, ~1.2°C warmer, ~15% dropout
    wu_mask  = np.random.random(n_hours) > 0.15
    wu_temp  = np.where(wu_mask, temp_base + 1.2 + np.random.randn(n_hours) * 0.4, np.nan)
    wu_hum   = np.where(wu_mask, humidity_base - 2.0 + np.random.randn(n_hours) * 2.0, np.nan)
    wu_wind  = np.where(wu_mask, wind_base * 0.88 + np.random.randn(n_hours) * 0.5, np.nan)

    df = pd.DataFrame({
        "timestamp":               timestamps,
        # Targets (ground truth)
        "temperature_c":           temp_base,
        "humidity_pct":            humidity_base,
        "wind_speed_kmh":          wind_base,
        "pressure_hpa":            pressure_base,
        "precipitation_mm":        precip_base,
        # NWP
        "nwp_gfs_temperature_c":   gfs_temp,
        "nwp_ecmwf_temperature_c": ecmwf_temp,
        "nwp_jma_temperature_c":   jma_temp,
        "nwp_gfs_humidity_pct":    gfs_hum,
        "nwp_ecmwf_humidity_pct":  ecmwf_hum,
        "nwp_jma_humidity_pct":    jma_hum,
        "nwp_gfs_wind_speed_kmh":  gfs_wind,
        "nwp_ecmwf_wind_speed_kmh": ecmwf_wind,
        "nwp_jma_wind_speed_kmh":  jma_wind,
        "nwp_gfs_pressure_hpa":    gfs_pres,
        "nwp_ecmwf_pressure_hpa":  ecmwf_pres,
        "nwp_jma_pressure_hpa":    jma_pres,
        # Weather Union
        "wu_temperature_c":        wu_temp,
        "wu_humidity_pct":         wu_hum,
        "wu_wind_speed_kmh":       wu_wind,
        "weather_union_available": wu_mask.astype(int),
    })

    wu_coverage = wu_mask.mean() * 100
    print(f"  Generated {n_hours} hours of synthetic data")
    print(f"  Weather Union coverage: {wu_coverage:.1f}%")
    print(f"  Date range: {timestamps[0].date()} → {timestamps[-1].date()}")
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Train Weather AI forecasting models",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--target",       default="temperature_c",
                        choices=["temperature_c", "humidity_pct", "wind_speed_kmh",
                                 "pressure_hpa", "precipitation_mm"],
                        help="Target variable to forecast")
    parser.add_argument("--horizon",      type=int, default=6,
                        help="Forecast horizon in hours")
    parser.add_argument("--data-hours",   type=int, default=3000,
                        help="Hours of synthetic training data")
    parser.add_argument("--artifact-dir", default="backend/artifacts",
                        help="Directory to save trained model artifacts")
    args = parser.parse_args()

    print("\n" + "=" * 62)
    print("  Weather AI Platform — Training Pipeline")
    print("=" * 62)
    print(f"  Target variable : {args.target}")
    print(f"  Forecast horizon: {args.horizon}h")
    print(f"  Artifact dir    : {args.artifact_dir}")
    print("=" * 62 + "\n")

    # Generate / load training data
    print("► Generating training data …")
    df = generate_synthetic_data(n_hours=args.data_hours)

    # Run full pipeline
    print("\n► Starting training pipeline …")
    from app.ml.training.pipeline import WeatherForecastingPipeline

    pipeline = WeatherForecastingPipeline(
        artifact_dir=args.artifact_dir,
        horizon_hours=args.horizon,
        target_var=args.target,
    )

    try:
        metrics = pipeline.run(df)
    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # Print results table
    print("\n" + "=" * 62)
    print("  TRAINING COMPLETE — MODEL PERFORMANCE")
    print("=" * 62)
    print(f"  {'Model':<14} {'MAE':>8} {'RMSE':>8} {'R²':>7} {'MAPE':>8}")
    print("  " + "-" * 48)
    for model_name, m in metrics.items():
        if model_name in ("ablation", "evaluation_notes") or not isinstance(m, dict):
            continue
        mae  = m.get("mae",  "—")
        rmse = m.get("rmse", "—")
        r2   = m.get("r2",   "—")
        mape = m.get("mape", "—")
        mae_s  = f"{mae:.4f}"  if isinstance(mae,  float) else str(mae)
        rmse_s = f"{rmse:.4f}" if isinstance(rmse, float) else str(rmse)
        r2_s   = f"{r2:.4f}"   if isinstance(r2,   float) else str(r2)
        mape_s = f"{mape:.2f}%" if isinstance(mape, float) else str(mape)
        print(f"  {model_name:<14} {mae_s:>8} {rmse_s:>8} {r2_s:>7} {mape_s:>8}")

    if "ablation" in metrics and metrics["ablation"]:
        print("\n" + "=" * 76)
        print("  ABLATION STUDY (Weather Union & ML Accuracy Contribution)")
        print("=" * 76)
        print(f"  {'Experiment':<32} {'MAE':>8} {'RMSE':>8} {'Abs Imp':>9} {'Pct Imp':>10}")
        print("  " + "-" * 72)
        for row in metrics["ablation"]:
            if not isinstance(row, dict):
                continue
            exp   = row.get("experiment") or row.get("model", "?")
            mae   = row.get("mae", "—")
            rmse  = row.get("rmse", "—")
            abs_i = row.get("absolute_improvement", row.get("absolute_improvement_vs_baseline"))
            pct_i = row.get("percentage_improvement", row.get("percent_improvement_vs_baseline"))
            mae_s = f"{mae:.4f}" if isinstance(mae, float) else str(mae)
            rmse_s = f"{rmse:.4f}" if isinstance(rmse, float) else str(rmse)
            abs_s = f"{abs_i:+.4f}" if isinstance(abs_i, float) else "baseline"
            pct_s = f"{pct_i:+.2f}%" if isinstance(pct_i, float) else "0.00%"
            print(f"  {exp:<32} {mae_s:>8} {rmse_s:>8} {abs_s:>9} {pct_s:>10}")

    print(f"\n✓ Artifacts saved to: {args.artifact_dir}\n")


if __name__ == "__main__":
    main()
