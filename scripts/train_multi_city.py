#!/usr/bin/env python3
"""
Multi-City 1-Year Factual Weather Training Runner.
Fetches 1 year of real historical data (ERA5 + GFS + ECMWF + JMA) from Open-Meteo
and trains the Weather AI forecasting pipeline across multiple Indian cities.

Supported cities:
  jaipur, bengaluru, hyderabad, mumbai, chennai, delhi, kolkata, pune,
  ahmedabad, lucknow, chandigarh, bhopal, patna, kochi, etc.

Usage:
  python scripts/train_multi_city.py
  python scripts/train_multi_city.py --cities jaipur bengaluru hyderabad mumbai chennai
  python scripts/train_multi_city.py --days 365 --save-csv
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root and backend directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx
import numpy as np
import pandas as pd
from app.ml.training.pipeline import WeatherForecastingPipeline
from scripts.fetch_and_train import (
    CITY_COORDS,
    build_training_dataset,
    fetch_historical_truth,
    fetch_nwp_hindcast,
)

DEFAULT_CITIES = [
    "jaipur",
    "bengaluru",
    "hyderabad",
    "mumbai",
    "chennai",
    "delhi",
    "kolkata",
    "pune",
    "ahmedabad",
    "lucknow",
    "chandigarh",
    "bhopal",
    "patna",
    "kochi",
]


def train_single_city(city: str, days: int = 365, target: str = "temperature_c", horizon: int = 6, save_csv: bool = True):
    city_clean = city.strip().lower()
    if city_clean not in CITY_COORDS:
        print(f"[-] Unknown city '{city}'. Skipping.")
        return None

    lat, lon = CITY_COORDS[city_clean]
    city_title = city_clean.title()
    print(f"\n{'=' * 60}")
    print(f"  Fetching & Training: {city_title} ({lat:.4f}N, {lon:.4f}E)")
    print(f"  Historical Window : {days} days of factual ERA5 + NWP hindcasts")
    print(f"{'=' * 60}")

    try:
        df = build_training_dataset(lat, lon, days=days, city_name=city_clean)
    except Exception as e:
        print(f"[-] ERROR: Failed fetching data for {city_title}: {e}")
        return None

    if df.empty or len(df) < 200:
        print(f"[-] ERROR: Failed fetching data for {city_title}")
        return None

    if save_csv:
        csv_dir = Path("data")
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir / f"data_{city_clean}.csv"
        df.to_csv(csv_path, index=False)
        print(f"  [+] Saved dataset: {csv_path}")

    # City-specific artifact directory
    city_artifact_dir = BACKEND_DIR / "artifacts" / city_clean
    city_artifact_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [*] Training ML pipeline for {city_title} ({len(df)} samples) ...")
    pipeline = WeatherForecastingPipeline(
        artifact_dir=str(city_artifact_dir),
        horizon_hours=horizon,
        target_var=target,
    )

    try:
        metrics = pipeline.run(df)
        print(f"  [+] Finished training {city_title} successfully.")
        return {
            "city": city_title,
            "lat": lat,
            "lon": lon,
            "samples": len(df),
            "metrics": metrics,
            "artifact_dir": str(city_artifact_dir),
        }
    except Exception as e:
        print(f"  [-] Training failed for {city_title}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Multi-City Factual Weather AI Training Runner")
    parser.add_argument(
        "--cities",
        nargs="+",
        default=DEFAULT_CITIES,
        help="List of cities to train for (default: 14 cities)",
    )
    parser.add_argument("--days", type=int, default=365, help="Historical days (factual)")
    parser.add_argument("--target", default="temperature_c", help="Target weather variable")
    parser.add_argument("--horizon", type=int, default=6, help="Forecast horizon hours")
    parser.add_argument("--save-csv", action="store_true", default=True, help="Save city CSV datasets")
    args = parser.parse_args()

    print("\n" + "=" * 64)
    print("  WEATHER AI - MULTI-CITY FACTUAL TRAINING SUITE")
    print(f"  Total Cities: {len(args.cities)}")
    print(f"  Target: {args.target} @ +{args.horizon}h | Window: {args.days} days")
    print("=" * 64)

    all_results = []
    start_time = time.time()

    for idx, city in enumerate(args.cities, 1):
        print(f"\n>>> Progress: City {idx}/{len(args.cities)} ({city.title()})")
        res = train_single_city(
            city=city,
            days=args.days,
            target=args.target,
            horizon=args.horizon,
            save_csv=args.save_csv,
        )
        if res:
            all_results.append(res)
        time.sleep(1)  # Rate limit courtesy

    total_time = time.time() - start_time

    # Summary table
    print("\n" + "=" * 70)
    print("  MULTI-CITY TRAINING SUMMARY (1-YEAR FACTUAL DATA)")
    print("=" * 70)
    print(f"  {'City':<15} {'Samples':>8} {'NWP MAE':>10} {'RF MAE':>8} {'XGB MAE':>9} {'ANN MAE':>9} {'Best':>8}")
    print("  " + "-" * 66)

    summary_records = []
    for r in all_results:
        city = r["city"]
        samples = r["samples"]
        m = r["metrics"]
        rf_mae = m.get("RF", {}).get("mae", float("nan"))
        xgb_mae = m.get("XGBoost", {}).get("mae", float("nan"))
        ann_mae = m.get("ANN", {}).get("mae", float("nan"))

        # Raw NWP baseline from ablation
        nwp_mae = float("nan")
        if "ablation" in m and isinstance(m["ablation"], list):
            for row in m["ablation"]:
                if row.get("model") == "NWP only":
                    nwp_mae = row.get("mae", float("nan"))

        best_mae = min([x for x in [rf_mae, xgb_mae, ann_mae] if not np.isnan(x)], default=float("nan"))
        best_name = "RF" if best_mae == rf_mae else ("XGB" if best_mae == xgb_mae else "ANN")

        print(
            f"  {city:<15} {samples:>8} "
            f"{f'{nwp_mae:.2f}' if not np.isnan(nwp_mae) else '—':>10} "
            f"{f'{rf_mae:.2f}' if not np.isnan(rf_mae) else '—':>8} "
            f"{f'{xgb_mae:.2f}' if not np.isnan(xgb_mae) else '—':>9} "
            f"{f'{ann_mae:.2f}' if not np.isnan(ann_mae) else '—':>9} "
            f"{best_name:>8}"
        )

        summary_records.append({
            "city": city,
            "samples": samples,
            "nwp_mae": nwp_mae,
            "rf_mae": rf_mae,
            "xgb_mae": xgb_mae,
            "ann_mae": ann_mae,
            "best_mae": best_mae,
            "best_model": best_name,
        })

    print("=" * 70)
    print(f"Completed in {total_time:.1f} seconds. All city models saved in backend/artifacts/<city>/\n")

    # Save summary json
    summary_path = BACKEND_DIR / "artifacts" / "multi_city_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_records, f, indent=2, default=str)
    print(f"Summary report written to {summary_path}")


if __name__ == "__main__":
    main()
