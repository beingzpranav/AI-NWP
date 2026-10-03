"""
ML Data Ingestion and Synthetic Data Generation Module.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import numpy as np
import pandas as pd


def generate_synthetic_weather_dataset(n_hours: int = 3000, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates realistic synthetic hourly weather data with NWP systematic biases
    and localized Weather Union urban station observations.
    """
    np.random.seed(random_seed)
    base = datetime(2023, 1, 1, tzinfo=timezone.utc)
    timestamps = [base + timedelta(hours=i) for i in range(n_hours)]
    hours = np.array([t.hour for t in timestamps])
    doys  = np.array([t.timetuple().tm_yday for t in timestamps])

    temp_diurnal  = 5.0  * np.sin(2 * np.pi * (hours - 6) / 24)
    temp_seasonal = 8.0  * np.sin(2 * np.pi * (doys  - 80) / 365)
    temp_base     = 26.0 + temp_diurnal + temp_seasonal + np.random.randn(n_hours) * 1.2

    humidity_base  = np.clip(65 - 0.4 * temp_diurnal + np.random.randn(n_hours) * 4, 15, 100)
    pressure_base  = 1013 + 2 * np.sin(2 * np.pi * doys / 365) + np.random.randn(n_hours) * 0.8
    wind_base      = np.abs(8 + np.random.randn(n_hours) * 3)
    precip_base    = np.where(np.random.random(n_hours) > 0.85,
                              np.abs(np.random.exponential(2.0, n_hours)), 0.0)

    # NWP forecasts with realistic biases
    gfs_temp   = temp_base  + 0.6  + np.random.randn(n_hours) * 0.9
    ecmwf_temp = temp_base  + 0.15 + np.random.randn(n_hours) * 0.5
    jma_temp   = temp_base  + 1.1  + np.random.randn(n_hours) * 1.1

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

    return pd.DataFrame({
        "timestamp":               timestamps,
        "temperature_c":           temp_base,
        "humidity_pct":            humidity_base,
        "wind_speed_kmh":          wind_base,
        "pressure_hpa":            pressure_base,
        "precipitation_mm":        precip_base,
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
        "wu_temperature_c":        wu_temp,
        "wu_humidity_pct":         wu_hum,
        "wu_wind_speed_kmh":       wu_wind,
        "weather_union_available": wu_mask.astype(int),
    })

__all__ = ["generate_synthetic_weather_dataset"]
