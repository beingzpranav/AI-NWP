#!/usr/bin/env python3
"""
Fetch REAL historical weather data from Open-Meteo and train the full ML pipeline.

Data sources (all real, no synthetic):
  - Open-Meteo Historical API: past GFS/ECMWF/ERA5 reanalysis (truth)
  - Open-Meteo Forecast API:   GFS, ECMWF, JMA model hindcasts
  - Weather Union:             real observations (appended live)

Usage:
    cd weather-ai-platform
    python scripts/fetch_and_train.py --city delhi
    python scripts/fetch_and_train.py --lat 12.97 --lon 77.59  (Bengaluru)
    python scripts/fetch_and_train.py --city mumbai --days 90
"""
import argparse
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import httpx
import numpy as np
import pandas as pd

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

CITY_COORDS = {
    "delhi":         (28.6139, 77.2090),
    "jaipur":        (26.9124, 75.7873),
    "bengaluru":     (12.9716, 77.5946),
    "bangalore":     (12.9716, 77.5946),
    "hyderabad":     (17.3850, 78.4867),
    "heydarabad":    (17.3850, 78.4867),
    "mumbai":        (19.0760, 72.8777),
    "chennai":       (13.0827, 80.2707),
    "kolkata":       (22.5726, 88.3639),
    "pune":          (18.5204, 73.8567),
    "ahmedabad":     (23.0225, 72.5714),
    "lucknow":       (26.8467, 80.9462),
    "chandigarh":    (30.7333, 76.7794),
    "bhopal":        (23.2599, 77.4126),
    "patna":         (25.5941, 85.1376),
    "kochi":         (9.9312, 76.2673),
    "surat":         (21.1702, 72.8311),
    "visakhapatnam": (17.6868, 83.2185),
    "indore":        (22.7196, 75.8577),
    "nagpur":        (21.1458, 79.0882),
}

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
]

# Open-Meteo model IDs for hindcast
NWP_MODELS = {
    "GFS":   "gfs_seamless",
    "ECMWF": "ecmwf_ifs025",
    "JMA":   "jma_seamless",
}


def _get_with_retry(url: str, params: dict, max_retries: int = 5) -> dict:
    """HTTP GET request with automatic retry and rate-limit backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = httpx.get(url, params=params, timeout=60)
            if resp.status_code == 429:
                wait = attempt * 4
                print(f"    [Rate Limited 429] Waiting {wait}s (attempt {attempt}/{max_retries})...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == max_retries:
                raise e
            wait = attempt * 3
            print(f"    [Network/API Retry] {e}. Waiting {wait}s (attempt {attempt}/{max_retries})...")
            time.sleep(wait)
    raise RuntimeError(f"Failed request to {url}")


def fetch_historical_truth(lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """
    Fetch ERA5 reanalysis as ground truth (best available real observations).
    ERA5 is the gold standard — ECMWF's reanalysis product.
    """
    print(f"  Fetching ERA5 reanalysis truth: {start} → {end} ...")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start,
        "end_date":   end,
        "hourly":     ",".join(HOURLY_VARS),
        "timezone":   "UTC",
        "timeformat": "iso8601",
    }
    data = _get_with_retry(url, params)
    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.drop(columns=["time"])
    df = df.rename(columns={
        "temperature_2m":       "temperature_c",
        "relative_humidity_2m": "humidity_pct",
        "precipitation":        "precipitation_mm",
        "surface_pressure":     "pressure_hpa",
        "wind_speed_10m":       "wind_speed_kmh",
        "wind_direction_10m":   "wind_direction_deg",
        "cloud_cover":          "cloud_cover_pct",
    })
    print(f"    Got {len(df)} hourly observations (ERA5)")
    return df


def fetch_nwp_hindcast(model: str, lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    """
    Fetch NWP model hindcast (what the model actually predicted, not analysis).
    Uses Open-Meteo forecast archive — real NWP output.
    """
    print(f"  Fetching {model} hindcast: {start} → {end} ...")
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": start,
        "end_date":   end,
        "hourly":     ",".join(HOURLY_VARS),
        "models":     NWP_MODELS[model],
        "timezone":   "UTC",
        "timeformat": "iso8601",
    }
    try:
        data = _get_with_retry(url, params)
        hourly = data["hourly"]
        df = pd.DataFrame(hourly)
        df["timestamp"] = pd.to_datetime(df["time"], utc=True)
        df = df.drop(columns=["time"])
        col_map = {
            "temperature_2m":       f"nwp_{model.lower()}_temperature_c",
            "relative_humidity_2m": f"nwp_{model.lower()}_humidity_pct",
            "precipitation":        f"nwp_{model.lower()}_precipitation_mm",
            "surface_pressure":     f"nwp_{model.lower()}_pressure_hpa",
            "wind_speed_10m":       f"nwp_{model.lower()}_wind_speed_kmh",
            "wind_direction_10m":   f"nwp_{model.lower()}_wind_direction_deg",
            "cloud_cover":          f"nwp_{model.lower()}_cloud_cover_pct",
        }
        df = df.rename(columns=col_map)
        print(f"    Got {len(df)} rows for {model}")
        return df
    except Exception as e:
        print(f"    WARNING: {model} hindcast failed: {e} — skipping")
        return pd.DataFrame()


CITY_METAR = {
    "delhi": "VIDP",
    "mumbai": "VABB",
    "bengaluru": "VOBL",
    "bangalore": "VOBL",
    "hyderabad": "VOHS",
    "heydarabad": "VOHS",
    "chennai": "VOMM",
    "kolkata": "VECC",
    "jaipur": "VIJP",
    "pune": "VAPO",
    "ahmedabad": "VAAH",
    "lucknow": "VILK",
    "chandigarh": "VICG",
    "bhopal": "VABP",
    "patna": "VEPT",
    "kochi": "VOCI",
}


def fetch_metar_truth(station_code: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch real station observations from Iowa Mesonet ASOS/METAR archive.
    """
    print(f"  Fetching METAR station truth ({station_code}): {start} → {end} ...")
    try:
        s_dt = datetime.strptime(start, "%Y-%m-%d")
        e_dt = datetime.strptime(end, "%Y-%m-%d")
        url = (
            f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station={station_code}"
            f"&data=tmpc&data=relh&data=sknt&data=alti"
            f"&year1={s_dt.year}&month1={s_dt.month}&day1={s_dt.day}"
            f"&year2={e_dt.year}&month2={e_dt.month}&day2={e_dt.day}"
            "&tz=Etc/UTC&format=onlycomma&latlon=no&missing=M&trace=T&direct=no&report_type=3&report_type=4"
        )
        resp = httpx.get(url, timeout=60)
        resp.raise_for_status()
        import io
        m_df = pd.read_csv(io.StringIO(resp.text), na_values=["M"], parse_dates=["valid"])
        m_df["valid"] = pd.to_datetime(m_df["valid"], utc=True)
        m_df = m_df.dropna(subset=["tmpc"])
        num_cols = [c for c in ["tmpc", "relh", "sknt", "alti"] if c in m_df.columns]
        m_df = m_df.set_index("valid")[num_cols].resample("1h", label="right", closed="right").mean(numeric_only=True)
        m_df = m_df.reset_index().rename(columns={
            "valid": "timestamp",
            "tmpc": "temperature_c",
            "relh": "humidity_pct",
            "sknt": "wind_speed_kts",
            "alti": "pressure_inches"
        })
        m_df["wind_speed_kmh"] = m_df["wind_speed_kts"] * 1.852
        m_df["pressure_hpa"] = m_df["pressure_inches"] * 33.8639
        print(f"    Got {len(m_df)} hourly METAR station observations")
        return m_df
    except Exception as e:
        print(f"    WARNING: METAR fetch failed for {station_code}: {e} — falling back to ERA5")
        return pd.DataFrame()


def build_training_dataset(lat: float, lon: float, days: int = 180, city_name: str = None) -> pd.DataFrame:
    """
    Builds a real training dataset:
    - METAR station observations (where available) + ERA5 reanalysis
    - GFS, ECMWF, JMA hindcasts as NWP features
    - WU bias columns as NaN (populated during live operation)
    """
    end_date   = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days + 2)).strftime("%Y-%m-%d")

    print(f"\nFetching real historical data: {start_date} to {end_date}")
    print(f"Location: {lat:.3f}N, {lon:.3f}E  ({days} days)")

    # 1. Ground truth from ERA5
    truth = fetch_historical_truth(lat, lon, start_date, end_date)

    # Overlay METAR real station truth if available
    if city_name and city_name.lower() in CITY_METAR:
        st_code = CITY_METAR[city_name.lower()]
        metar_df = fetch_metar_truth(st_code, start_date, end_date)
        if not metar_df.empty:
            metar_df = metar_df.set_index("timestamp")
            truth = truth.set_index("timestamp")
            for col in ["temperature_c", "humidity_pct", "wind_speed_kmh", "pressure_hpa"]:
                if col in metar_df.columns and col in truth.columns:
                    truth[col] = metar_df[col].combine_first(truth[col])
            truth = truth.reset_index()

    # 2. Merge NWP hindcasts
    merged = truth.copy()
    for model in ["GFS", "ECMWF", "JMA"]:
        time.sleep(1)  # be polite to Open-Meteo
        nwp_df = fetch_nwp_hindcast(model, lat, lon, start_date, end_date)
        if not nwp_df.empty:
            nwp_df = nwp_df.set_index("timestamp")
            merged = merged.set_index("timestamp").join(
                nwp_df, how="left"
            ).reset_index()

    # 3. Add WU placeholder columns (NaN — filled at inference time from live WU)
    merged["wu_temperature_c"]  = np.nan
    merged["wu_humidity_pct"]   = np.nan
    merged["wu_wind_speed_kmh"] = np.nan
    merged["weather_union_available"] = 0

    # 4. Clean up
    merged = merged.sort_values("timestamp").reset_index(drop=True)
    merged = merged.drop_duplicates(subset=["timestamp"])

    # Report
    nwp_cols = [c for c in merged.columns if c.startswith("nwp_")]
    print(f"\n  Dataset: {len(merged)} rows × {len(merged.columns)} columns")
    print(f"  NWP columns: {len(nwp_cols)}")
    print(f"  Date range: {merged['timestamp'].min()} → {merged['timestamp'].max()}")
    print(f"  Missing temp: {merged['temperature_c'].isna().sum()}")

    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Fetch REAL data and train Weather AI models",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--city",         default=None,
                        help="City name: delhi, mumbai, bengaluru, chennai, ...")
    parser.add_argument("--lat",          type=float, default=None)
    parser.add_argument("--lon",          type=float, default=None)
    parser.add_argument("--days",         type=int, default=180,
                        help="Days of historical data to fetch (max ~365)")
    parser.add_argument("--target",       default="temperature_c")
    parser.add_argument("--horizon",      type=int, default=6)
    parser.add_argument("--artifact-dir", default="backend/artifacts")
    parser.add_argument("--save-csv",     action="store_true",
                        help="Save fetched dataset to CSV for inspection")
    args = parser.parse_args()

    # Resolve coordinates
    if args.city:
        city = args.city.lower()
        if city not in CITY_COORDS:
            print(f"Unknown city '{city}'. Available: {', '.join(CITY_COORDS)}")
            sys.exit(1)
        lat, lon = CITY_COORDS[city]
        label = args.city.title()
    elif args.lat and args.lon:
        lat, lon = args.lat, args.lon
        label = f"{lat:.3f},{lon:.3f}"
    else:
        # Default: Delhi
        lat, lon = CITY_COORDS["delhi"]
        label = "Delhi"

    print("\n" + "=" * 62)
    print("  Weather AI — Real Data Training Pipeline")
    print("=" * 62)
    print(f"  Location : {label} ({lat}, {lon})")
    print(f"  History  : {args.days} days of real ERA5 + NWP hindcasts")
    print(f"  Target   : {args.target} @ +{args.horizon}h")
    print("=" * 62)

    # Fetch real data
    df = build_training_dataset(lat, lon, days=args.days, city_name=args.city or label)

    if args.save_csv:
        csv_path = f"data_{label.lower().replace(' ', '_')}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n  Dataset saved to: {csv_path}")

    if df.empty or len(df) < 200:
        print("ERROR: Not enough data fetched. Check internet connection.")
        sys.exit(1)

    # Train
    print(f"\n► Starting training on {len(df)} REAL data points ...")
    from app.ml.training.pipeline import WeatherForecastingPipeline

    pipeline = WeatherForecastingPipeline(
        artifact_dir=args.artifact_dir,
        horizon_hours=args.horizon,
        target_var=args.target,
    )

    try:
        metrics = pipeline.run(df)
    except Exception as e:
        import traceback
        print(f"\n✗ Training failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Print results
    print("\n" + "=" * 62)
    print("  TRAINING COMPLETE — REAL DATA RESULTS")
    print("=" * 62)
    print(f"  {'Model':<14} {'MAE':>8} {'RMSE':>8} {'R²':>7}")
    print("  " + "-" * 42)
    for name, m in metrics.items():
        if name in ("ablation", "evaluation_notes") or not isinstance(m, dict):
            continue
        mae  = m.get("mae")
        rmse = m.get("rmse")
        r2   = m.get("r2")
        print(f"  {name:<14} {f'{mae:.3f}' if mae else '—':>8} "
              f"{f'{rmse:.3f}' if rmse else '—':>8} "
              f"{f'{r2:.3f}' if r2 else '—':>7}")

    if "ablation" in metrics and metrics["ablation"]:
        print("\n  ABLATION (does each component help?):")
        for row in metrics["ablation"]:
            if isinstance(row, dict):
                imp = row.get("percent_improvement_vs_baseline")
                imp_s = f"  {imp:+.1f}% vs NWP-only" if isinstance(imp, float) else ""
                print(f"    {row.get('model','?'):<20} MAE={row.get('mae','?')}{imp_s}")

    print(f"\n✓ Artifacts saved to: {args.artifact_dir}")
    print(f"✓ Restart the backend to load new models automatically.\n")


if __name__ == "__main__":
    main()
