"""
Forecasting Engine — orchestrates the complete pipeline:
NWP → Weather Union → Feature Engineering → Base Models → Dynamic Weighting → ANN → Forecast
"""
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from app.services.weather_union import get_weather_union_client
from app.services.nwp import get_nwp_client
from app.ml.models.dynamic_weighting import DynamicModelWeighter, FALLBACK_WEIGHTS
from app.schemas.weather import (
    ForecastPoint, ForecastResponse, LocationResponse,
    NWPForecastResponse, ModelWeights, UncertaintyBands,
)
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Artifact-weight cache: city_key → weights dict
_city_weight_cache: Dict[str, Dict[str, float]] = {}


def _nearest(forecasts: list, target_time: datetime):
    """Return the NWP point whose valid_time is closest to target_time."""
    if not forecasts:
        return None
    best = min(
        forecasts,
        key=lambda f: abs((f.valid_time - target_time).total_seconds())
    )
    if abs((best.valid_time - target_time).total_seconds()) <= 5400:
        return best
    return None


def _load_city_weights(city_name: Optional[str]) -> Dict[str, float]:
    """
    Load model MAE scores from a city-specific (or global) metadata.json
    and compute inverse-MAE reliability weights — identical algorithm to DynamicModelWeighter.
    Falls back to FALLBACK_WEIGHTS if no artifacts exist.
    """
    cache_key = (city_name or "global").lower().replace(" ", "_")
    if cache_key in _city_weight_cache:
        return _city_weight_cache[cache_key]

    # Find the right metadata.json: try city-specific then global
    artifact_root = Path(settings.model_artifact_dir)
    candidates = []
    if city_name:
        city_slug = city_name.lower().replace(" ", "_")
        candidates += [
            artifact_root / city_slug / "metadata.json",
            Path("artifacts") / city_slug / "metadata.json",
            Path("backend/artifacts") / city_slug / "metadata.json",
            Path(__file__).parent.parent.parent.parent / "artifacts" / city_slug / "metadata.json",
            Path(__file__).parent.parent.parent.parent / "backend" / "artifacts" / city_slug / "metadata.json",
        ]
    candidates += [
        artifact_root / "metadata.json",
        Path("artifacts") / "metadata.json",
        Path("backend/artifacts") / "metadata.json",
        Path(__file__).parent.parent.parent.parent / "artifacts" / "metadata.json",
        Path(__file__).parent.parent.parent.parent / "backend" / "artifacts" / "metadata.json",
    ]

    meta = None
    for c in candidates:
        if c.exists():
            try:
                with open(c) as f:
                    meta = json.load(f)
                logger.info(f"loaded_city_weights_from path={c}")
                break
            except Exception:
                continue

    if meta is None:
        result = dict(FALLBACK_WEIGHTS)
        _city_weight_cache[cache_key] = result
        return result

    try:
        metrics = meta.get("metrics", {})
        mae_rf  = metrics.get("RF",      {}).get("mae")
        mae_xgb = metrics.get("XGBoost", {}).get("mae")
        mae_ada = metrics.get("AdaBoost",{}).get("mae")
        mae_ann = metrics.get("ANN",     {}).get("mae")

        # Best ML model MAE (minimum across trained models)
        ml_maes = [m for m in [mae_rf, mae_xgb, mae_ada, mae_ann] if m is not None]
        best_ml_mae = min(ml_maes) if ml_maes else None

        # NWP-only baseline
        nwp_mae = None
        for row in metrics.get("ablation", []):
            if isinstance(row, dict) and row.get("model") == "NWP only":
                nwp_mae = row.get("mae")
                break
        if nwp_mae is None:
            nwp_mae = 3.14

        EPSILON = 1e-6
        # Split NWP baseline into per-model MAE using known accuracy ratios
        nwp_ecmwf_mae = nwp_mae * 0.85
        nwp_gfs_mae   = nwp_mae * 1.05
        nwp_jma_mae   = nwp_mae * 1.10

        rel_ecmwf = 1.0 / (nwp_ecmwf_mae + EPSILON)
        rel_gfs   = 1.0 / (nwp_gfs_mae   + EPSILON)
        rel_jma   = 1.0 / (nwp_jma_mae   + EPSILON)
        rel_ml    = 1.0 / (best_ml_mae    + EPSILON) if best_ml_mae else rel_ecmwf * 1.3

        total = rel_gfs + rel_ecmwf + rel_jma + rel_ml
        result = {
            "GFS":   round(rel_gfs   / total, 4),
            "ECMWF": round(rel_ecmwf / total, 4),
            "JMA":   round(rel_jma   / total, 4),
            "ML":    round(rel_ml    / total, 4),
        }
        logger.info(f"city_weights_computed: city={cache_key}, weights={result}, best_ml_mae={best_ml_mae}, nwp_mae={nwp_mae}")
    except Exception as e:
        logger.warning(f"city_weights_fallback: city={cache_key}, error={e}")
        result = dict(FALLBACK_WEIGHTS)

    _city_weight_cache[cache_key] = result
    return result


from app.ml.inference.engine import get_ml_inference_engine, get_city_ml_engine

# Known dataset cities with exact coordinates
KNOWN_CITIES = {
    "delhi":         (28.6139, 77.2090, "New Delhi"),
    "jaipur":        (26.9124, 75.7873, "Jaipur"),
    "bengaluru":     (12.9716, 77.5946, "Bengaluru"),
    "hyderabad":     (17.3850, 78.4867, "Hyderabad"),
    "mumbai":        (19.0760, 72.8777, "Mumbai"),
    "chennai":       (13.0827, 80.2707, "Chennai"),
    "kolkata":       (22.5726, 88.3639, "Kolkata"),
    "pune":          (18.5204, 73.8567, "Pune"),
    "ahmedabad":     (23.0225, 72.5714, "Ahmedabad"),
    "lucknow":       (26.8467, 80.9462, "Lucknow"),
    "chandigarh":    (30.7333, 76.7794, "Chandigarh"),
    "bhopal":        (23.2599, 77.4126, "Bhopal"),
    "patna":         (25.5941, 85.1376, "Patna"),
    "kochi":         (9.9312,  76.2673, "Kochi"),
}


def resolve_city_from_coords(lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
    """Returns (city_slug, display_name) for closest known city within 150km."""
    best_slug = None
    best_name = None
    best_dist = float("inf")
    for slug, (c_lat, c_lon, display_name) in KNOWN_CITIES.items():
        d_lat = (lat - c_lat) * 111.0
        d_lon = (lon - c_lon) * 111.0 * np.cos(np.radians(lat))
        dist = float(np.sqrt(d_lat ** 2 + d_lon ** 2))
        if dist < best_dist and dist <= 150.0:
            best_dist = dist
            best_slug = slug
            best_name = display_name
    return best_slug, best_name


class ForecastingEngine:
    def __init__(self):
        self.wu_client = get_weather_union_client()
        self.nwp_client = get_nwp_client()
        self.weighter = DynamicModelWeighter()

    async def generate_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_hours: int = 48,
        location_response: Optional[LocationResponse] = None,
    ) -> ForecastResponse:
        now = datetime.now(tz=timezone.utc)
        data_sources = {}

        # Determine city name for per-city model loading
        city_name = None
        if location_response:
            city_name = getattr(location_response, "city", None) or location_response.name

        # Resolve from coordinates if not provided or custom location
        resolved_slug, resolved_display = resolve_city_from_coords(latitude, longitude)
        if not city_name or city_name.lower() in ("custom location", "none", ""):
            city_name = resolved_slug
        elif resolved_slug and city_name.lower().replace(" ", "_") in KNOWN_CITIES:
            city_name = resolved_slug

        if location_response is None:
            location_response = LocationResponse(
                id=0,
                name=resolved_display or "Custom Location",
                city=resolved_display or "Custom Location",
                country="India",
                latitude=latitude,
                longitude=longitude,
                is_active=True,
                created_at=now,
                timezone="Asia/Kolkata",
            )
        elif getattr(location_response, "name", "") == "Custom Location" and resolved_display:
            location_response.name = resolved_display
            location_response.city = resolved_display

        # ── 1. Fetch NWP ───────────────────────────────────────
        nwp_data = await self.nwp_client.fetch_all_models(latitude, longitude, forecast_hours + 2)
        for model, forecasts in nwp_data.items():
            data_sources[model] = len(forecasts) > 0

        gfs_list   = nwp_data.get("GFS",   [])
        ecmwf_list = nwp_data.get("ECMWF", [])
        jma_list   = nwp_data.get("JMA",   [])

        # ── 2. Fetch Weather Union ─────────────────────────────
        wu_obs = None
        try:
            wu_obs = await self.wu_client.get_locality_weather(latitude, longitude)
        except Exception as e:
            logger.warning(f"wu_fetch_failed: {e}")
        data_sources["weather_union"] = wu_obs is not None and wu_obs.is_valid
        if wu_obs and wu_obs.is_valid:
            logger.info(f"wu_observation_received: temp={wu_obs.temperature_c}, station={wu_obs.station_id}")

        # ── 3. Load per-city ML engine + weights ───────────────
        ml_engine = get_city_ml_engine(city_name)
        artifact_weights = _load_city_weights(city_name)
        logger.info(f"forecast_using_weights: city={city_name}, weights={artifact_weights}, ml_loaded={ml_engine.is_loaded}")

        # ── 4. Get initial NWP estimates for h=0 (seed histories)
        h0_target = now + timedelta(hours=0)
        h0_gfs   = _nearest(gfs_list,   h0_target)
        h0_ecmwf = _nearest(ecmwf_list, h0_target)
        h0_jma   = _nearest(jma_list,   h0_target)

        def _best_nwp(attr, default):
            for f in [h0_ecmwf, h0_gfs, h0_jma]:
                if f is not None:
                    v = getattr(f, attr, None)
                    if v is not None:
                        return float(v)
            return default

        # Seed initial observation: prefer WU, then NWP
        init_temp  = (wu_obs.temperature_c if wu_obs and wu_obs.is_valid and wu_obs.temperature_c else
                      _best_nwp("temperature_c", 25.0))
        init_hum   = (wu_obs.humidity_pct if wu_obs and wu_obs.is_valid and wu_obs.humidity_pct else
                      _best_nwp("humidity_pct", 65.0))
        init_wind  = (wu_obs.wind_speed_kmh if wu_obs and wu_obs.is_valid and wu_obs.wind_speed_kmh else
                      _best_nwp("wind_speed_kmh", 10.0))
        init_press = _best_nwp("pressure_hpa", 1013.0)
        init_precip = _best_nwp("precipitation_mm", 0.0)

        # Rolling histories pre-filled for lag/rolling features
        PREFILL = 24
        hist_temp:   List[float] = [init_temp]   * PREFILL
        hist_hum:    List[float] = [init_hum]    * PREFILL
        hist_wind:   List[float] = [init_wind]   * PREFILL
        hist_press:  List[float] = [init_press]  * PREFILL
        hist_precip: List[float] = [init_precip] * PREFILL

        # ── 5. Build hourly forecast points ────────────────────
        points = []

        for h in range(forecast_hours):
            target_time = now + timedelta(hours=h)

            gfs_f   = _nearest(gfs_list,   target_time)
            ecmwf_f = _nearest(ecmwf_list, target_time)
            jma_f   = _nearest(jma_list,   target_time)

            available_models = [
                m for m, f in [("GFS", gfs_f), ("ECMWF", ecmwf_f), ("JMA", jma_f)]
                if f is not None
            ]

            # ── NWP weighting (city-specific) ──────────────────
            ml_w = artifact_weights.get("ML", 0.10) if ml_engine.is_loaded else 0.0
            nwp_budget = 1.0 - ml_w
            raw_nwp = {m: artifact_weights.get(m, FALLBACK_WEIGHTS.get(m, 0.0)) for m in available_models}
            raw_sum = sum(raw_nwp.values()) or 1.0
            nwp_weights = {m: (w / raw_sum) * nwp_budget for m, w in raw_nwp.items()}

            # Collect per-variable NWP values
            def nwp_val(attr):
                d = {}
                for m, f in [("GFS", gfs_f), ("ECMWF", ecmwf_f), ("JMA", jma_f)]:
                    if f is not None:
                        v = getattr(f, attr, None)
                        if v is not None:
                            d[m] = v
                return d

            temp_preds   = nwp_val("temperature_c")
            hum_preds    = nwp_val("humidity_pct")
            wind_preds   = nwp_val("wind_speed_kmh")
            precip_preds = nwp_val("precipitation_mm")
            press_preds  = nwp_val("pressure_hpa")
            wdir_preds   = nwp_val("wind_direction_deg")

            blended_temp   = DynamicModelWeighter.blend_predictions(temp_preds,   nwp_weights)
            blended_hum    = DynamicModelWeighter.blend_predictions(hum_preds,    nwp_weights)
            blended_wind   = DynamicModelWeighter.blend_predictions(wind_preds,   nwp_weights)
            blended_precip = DynamicModelWeighter.blend_predictions(precip_preds, nwp_weights)
            blended_press  = DynamicModelWeighter.blend_predictions(press_preds,  nwp_weights)
            blended_wdir   = DynamicModelWeighter.blend_predictions(wdir_preds,   nwp_weights)

            # Safe float helpers
            def sf(v, default):
                return float(v) if v is not None and not np.isnan(float(v)) else default

            proxy_temp  = sf(blended_temp,  hist_temp[-1])
            proxy_hum   = sf(blended_hum,   hist_hum[-1])
            proxy_wind  = sf(blended_wind,  hist_wind[-1])
            proxy_press = sf(blended_press, hist_press[-1])
            proxy_precip = sf(blended_precip, 0.0)

            # Override proxy with WU at h==0
            if h == 0 and wu_obs and wu_obs.is_valid:
                if wu_obs.temperature_c is not None:
                    proxy_temp = wu_obs.temperature_c
                if wu_obs.humidity_pct is not None:
                    proxy_hum = wu_obs.humidity_pct
                if wu_obs.wind_speed_kmh is not None:
                    proxy_wind = wu_obs.wind_speed_kmh

            # ── Build full feature dictionary ──────────────────
            t_vals = list(temp_preds.values())
            h_vals = list(hum_preds.values())
            w_vals = list(wind_preds.values())
            p_vals = list(press_preds.values())
            pr_vals = list(precip_preds.values())

            feat: Dict[str, float] = {}

            # Top-level obs features (index 0, 1 in feature list)
            feat["wind_direction_deg"] = sf(blended_wdir, 180.0)
            feat["cloud_cover_pct"]    = 50.0  # ERA5 feature; use neutral proxy

            # NWP per-model features
            for m_key, f_obj in [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]:
                feat[f"nwp_{m_key}_temperature_c"]      = sf(getattr(f_obj, "temperature_c",   None), proxy_temp)  if f_obj else proxy_temp
                feat[f"nwp_{m_key}_humidity_pct"]        = sf(getattr(f_obj, "humidity_pct",    None), proxy_hum)   if f_obj else proxy_hum
                feat[f"nwp_{m_key}_precipitation_mm"]    = sf(getattr(f_obj, "precipitation_mm",None), 0.0)         if f_obj else 0.0
                feat[f"nwp_{m_key}_pressure_hpa"]        = sf(getattr(f_obj, "pressure_hpa",    None), proxy_press) if f_obj else proxy_press
                feat[f"nwp_{m_key}_wind_speed_kmh"]      = sf(getattr(f_obj, "wind_speed_kmh",  None), proxy_wind)  if f_obj else proxy_wind
                feat[f"nwp_{m_key}_wind_direction_deg"]  = sf(getattr(f_obj, "wind_direction_deg",None), 180.0)     if f_obj else 180.0
                feat[f"nwp_{m_key}_cloud_cover_pct"]     = sf(getattr(f_obj, "cloud_cover_pct", None), 50.0)        if f_obj else 50.0

            # WU features
            wu_valid = wu_obs is not None and wu_obs.is_valid
            feat["wu_temperature_c"]       = sf(wu_obs.temperature_c  if wu_valid else None, proxy_temp)
            feat["wu_humidity_pct"]        = sf(wu_obs.humidity_pct   if wu_valid else None, proxy_hum)
            feat["wu_wind_speed_kmh"]      = sf(wu_obs.wind_speed_kmh if wu_valid else None, proxy_wind)
            feat["weather_union_available"]= float(int(wu_valid))

            # Temporal features
            feat["hour"]        = float(target_time.hour)
            feat["day_of_week"] = float(target_time.weekday())
            feat["day_of_year"] = float(target_time.timetuple().tm_yday)
            feat["month"]       = float(target_time.month)
            feat["season"]      = float((target_time.month % 12) // 3)
            feat["hour_sin"]    = np.sin(2 * np.pi * target_time.hour / 24)
            feat["hour_cos"]    = np.cos(2 * np.pi * target_time.hour / 24)
            feat["dow_sin"]     = np.sin(2 * np.pi * target_time.weekday() / 7)
            feat["dow_cos"]     = np.cos(2 * np.pi * target_time.weekday() / 7)
            feat["doy_sin"]     = np.sin(2 * np.pi * target_time.timetuple().tm_yday / 365)
            feat["doy_cos"]     = np.cos(2 * np.pi * target_time.timetuple().tm_yday / 365)
            feat["month_sin"]   = np.sin(2 * np.pi * target_time.month / 12)
            feat["month_cos"]   = np.cos(2 * np.pi * target_time.month / 12)

            # Lag features for ALL variables
            def lag_feats(hist, name):
                for lag in [1, 2, 3, 6, 12, 24]:
                    idx = -lag if len(hist) >= lag else 0
                    feat[f"{name}_lag_{lag}h"] = hist[idx] if hist else 0.0

            lag_feats(hist_temp,   "temperature_c")
            lag_feats(hist_hum,    "humidity_pct")
            lag_feats(hist_wind,   "wind_speed_kmh")
            lag_feats(hist_precip, "precipitation_mm")
            lag_feats(hist_press,  "pressure_hpa")

            # Rolling stats for ALL variables
            def roll_feats(hist, name, default_val):
                for win in [3, 6, 12, 24]:
                    sl = hist[-win:] if len(hist) >= win else hist
                    if sl:
                        arr = np.array(sl, dtype=np.float32)
                        feat[f"{name}_roll_mean_{win}h"] = float(np.mean(arr))
                        feat[f"{name}_roll_std_{win}h"]  = float(np.std(arr))
                        feat[f"{name}_roll_min_{win}h"]  = float(np.min(arr))
                        feat[f"{name}_roll_max_{win}h"]  = float(np.max(arr))
                    else:
                        feat[f"{name}_roll_mean_{win}h"] = default_val
                        feat[f"{name}_roll_std_{win}h"]  = 0.0
                        feat[f"{name}_roll_min_{win}h"]  = default_val
                        feat[f"{name}_roll_max_{win}h"]  = default_val

            roll_feats(hist_temp,   "temperature_c",   proxy_temp)
            roll_feats(hist_hum,    "humidity_pct",    proxy_hum)
            roll_feats(hist_wind,   "wind_speed_kmh",  proxy_wind)
            roll_feats(hist_precip, "precipitation_mm",0.0)
            roll_feats(hist_press,  "pressure_hpa",    proxy_press)

            # NWP ensemble disagreement features — temperature
            for var, vals, tup in [
                ("temperature_c",   t_vals,  [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]),
                ("humidity_pct",    h_vals,  [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]),
                ("wind_speed_kmh",  w_vals,  [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]),
                ("precipitation_mm",pr_vals, [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]),
                ("pressure_hpa",    p_vals,  [("gfs", gfs_f), ("ecmwf", ecmwf_f), ("jma", jma_f)]),
            ]:
                if vals:
                    feat[f"nwp_mean_{var}"]  = float(np.mean(vals))
                    feat[f"nwp_std_{var}"]   = float(np.std(vals)) if len(vals) > 1 else 0.0
                    feat[f"nwp_range_{var}"] = float(max(vals) - min(vals))
                else:
                    feat[f"nwp_mean_{var}"]  = getattr(feat, f"nwp_gfs_{var}", 0.0) if f"nwp_gfs_{var}" in feat else 0.0
                    feat[f"nwp_std_{var}"]   = 0.0
                    feat[f"nwp_range_{var}"] = 0.0

                # Pairwise diffs
                def gv(m_key): return feat.get(f"nwp_{m_key}_{var}", 0.0)
                feat[f"nwp_gfs_ecmwf_diff_{var}"]  = gv("gfs") - gv("ecmwf")
                feat[f"nwp_gfs_jma_diff_{var}"]    = gv("gfs") - gv("jma")
                feat[f"nwp_ecmwf_jma_diff_{var}"]  = gv("ecmwf") - gv("jma")

            # WU bias features (WU - NWP for each model)
            for m_key in ["gfs", "ecmwf", "jma"]:
                feat[f"bias_{m_key}_temperature_c"] = feat["wu_temperature_c"] - feat[f"nwp_{m_key}_temperature_c"]
                feat[f"bias_{m_key}_humidity_pct"]  = feat["wu_humidity_pct"]  - feat[f"nwp_{m_key}_humidity_pct"]
                feat[f"bias_{m_key}_wind_speed_kmh"]= feat["wu_wind_speed_kmh"]- feat[f"nwp_{m_key}_wind_speed_kmh"]

            # Model availability flags
            feat["gfs_available"]   = float(int(gfs_f is not None))
            feat["ecmwf_available"] = float(int(ecmwf_f is not None))
            feat["jma_available"]   = float(int(jma_f is not None))

            # ── ML Inference ──────────────────────────────────
            temp_std  = float(np.std(t_vals)) if len(t_vals) > 1 else 1.8
            confidence = min(1.0,
                (len(available_models) / 3.0) * 0.85
                + (0.1 if (wu_valid and h <= 6) else 0.0)
            )

            corrected_temp = proxy_temp  # start with NWP blend
            ml_pred = None
            ml_active = False

            if ml_engine.is_loaded:
                try:
                    p_val, ann_std, ann_conf = ml_engine.predict_point(feat, "temperature_c")
                    # Sanity check: ML prediction should be physically reasonable (within ±8°C of NWP consensus)
                    if abs(p_val - proxy_temp) <= 8.0:
                        ml_pred = p_val
                        temp_std = float(ann_std)
                        confidence = float(ann_conf)
                        ml_active = True
                    else:
                        logger.debug("ml_pred_out_of_range ml=%.1f nwp=%.1f", p_val, proxy_temp)
                except Exception as e:
                    logger.debug("ml_predict_exception: %s", e)

            # ── Multi-Model Ensemble Blend ──────────────────────
            if ml_active and ml_pred is not None:
                ml_disp = round(artifact_weights.get("ML", 0.35), 3)
                rem = 1.0 - ml_disp
                nwp_w = {m: artifact_weights.get(m, 0.0) for m in ["GFS", "ECMWF", "JMA"] if m in available_models}
                ns = sum(nwp_w.values()) or 1.0
                disp_weights = ModelWeights(
                    gfs=round(nwp_w.get("GFS",   0.0) / ns * rem, 3),
                    ecmwf=round(nwp_w.get("ECMWF",0.0) / ns * rem, 3),
                    jma=round(nwp_w.get("JMA",   0.0) / ns * rem, 3),
                    ml=ml_disp,
                )
                full_preds = {**temp_preds, "ML": ml_pred}
                full_weights = {
                    "GFS": disp_weights.gfs,
                    "ECMWF": disp_weights.ecmwf,
                    "JMA": disp_weights.jma,
                    "ML": disp_weights.ml,
                }
                ensemble_temp = DynamicModelWeighter.blend_predictions(full_preds, full_weights)
            else:
                disp_weights = ModelWeights(
                    gfs=round(nwp_weights.get("GFS",   0.0), 3),
                    ecmwf=round(nwp_weights.get("ECMWF",0.0), 3),
                    jma=round(nwp_weights.get("JMA",   0.0), 3),
                    ml=0.0,
                ) if available_models else None
                ensemble_temp = blended_temp

            # Ground truth actual observation at h=0 from Weather Union
            actual_temp = None
            if h == 0 and wu_valid and wu_obs.temperature_c is not None:
                actual_temp = wu_obs.temperature_c
                corrected_temp = wu_obs.temperature_c
            elif h == 1 and wu_valid and wu_obs.temperature_c is not None:
                corrected_temp = 0.60 * wu_obs.temperature_c + 0.40 * ensemble_temp
            elif h == 2 and wu_valid and wu_obs.temperature_c is not None:
                corrected_temp = 0.25 * wu_obs.temperature_c + 0.75 * ensemble_temp
            else:
                corrected_temp = ensemble_temp

            # Append to rolling histories for next step
            hist_temp.append(sf(corrected_temp, proxy_temp))
            hist_hum.append(sf(blended_hum,  proxy_hum))
            hist_wind.append(sf(blended_wind, proxy_wind))
            hist_press.append(sf(blended_press, proxy_press))
            hist_precip.append(sf(blended_precip, 0.0))

            # Keep histories at max 48 entries (saves memory)
            if len(hist_temp) > 48:
                hist_temp   = hist_temp[-48:]
                hist_hum    = hist_hum[-48:]
                hist_wind   = hist_wind[-48:]
                hist_press  = hist_press[-48:]
                hist_precip = hist_precip[-48:]

            points.append(ForecastPoint(
                valid_time=target_time,
                horizon_hours=h,
                temperature_c=self._r(corrected_temp),
                actual_temperature_c=self._r(actual_temp),
                humidity_pct=self._r(blended_hum),
                wind_speed_kmh=self._r(blended_wind),
                wind_direction_deg=self._r(blended_wdir),
                precipitation_mm=self._r(blended_precip, 2),
                pressure_hpa=self._r(blended_press, 1),
                uncertainty=UncertaintyBands(
                    temperature_sigma=round(max(0.0, temp_std), 2),
                    humidity_sigma=2.0,
                    wind_speed_sigma=2.0,
                    precipitation_sigma=0.5,
                    confidence_score=round(min(1.0, max(0.0, confidence)), 3),
                ),
                gfs=self._nwp_schema("GFS", gfs_f, h),
                ecmwf=self._nwp_schema("ECMWF", ecmwf_f, h),
                jma=self._nwp_schema("JMA", jma_f, h),
                weights=disp_weights,
            ))

        if not location_response:
            location_response = LocationResponse(
                id=0, name="Custom Location",
                latitude=latitude, longitude=longitude,
                is_active=True, created_at=now, timezone="UTC",
            )

        return ForecastResponse(
            location=location_response,
            generated_at=now,
            forecast_hours=forecast_hours,
            data_sources=data_sources,
            points=points,
        )

    @staticmethod
    def _r(val, decimals: int = 1) -> Optional[float]:
        if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
            return None
        return round(float(val), decimals)

    @staticmethod
    def _nwp_schema(model: str, f, horizon: int) -> Optional[NWPForecastResponse]:
        if f is None:
            return None
        return NWPForecastResponse(
            model_name=model,
            valid_time=f.valid_time,
            horizon_hours=horizon,
            temperature_c=f.temperature_c,
            humidity_pct=f.humidity_pct,
            wind_speed_kmh=f.wind_speed_kmh,
            precipitation_mm=f.precipitation_mm,
            pressure_hpa=f.pressure_hpa,
        )
