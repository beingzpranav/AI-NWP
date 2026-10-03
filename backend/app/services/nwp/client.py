"""
NWP client via Open-Meteo (free, no API key needed).
Fetches GFS, ECMWF IFS, and JMA GSM hourly forecasts.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

NWP_MODEL_MAP = {
    "GFS":   "gfs_seamless",
    "ECMWF": "ecmwf_ifs025",
    "JMA":   "jma_seamless",
}

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
]


class NWPForecastData:
    def __init__(self, model: str, valid_time: datetime, row: dict):
        self.model = model
        self.run_time = datetime.now(tz=timezone.utc)
        self.valid_time = valid_time
        self.horizon_hours = max(0, int((valid_time - self.run_time).total_seconds() / 3600))
        self.temperature_c:     Optional[float] = self._v(row.get("temperature_2m"))
        self.humidity_pct:      Optional[float] = self._v(row.get("relative_humidity_2m"))
        self.wind_speed_kmh:    Optional[float] = self._v(row.get("wind_speed_10m"))
        self.wind_direction_deg: Optional[float] = self._v(row.get("wind_direction_10m"))
        self.precipitation_mm:  Optional[float] = self._v(row.get("precipitation"))
        self.pressure_hpa:      Optional[float] = self._v(row.get("surface_pressure"))
        self.cloud_cover_pct:   Optional[float] = self._v(row.get("cloud_cover"))

    @staticmethod
    def _v(val) -> Optional[float]:
        if val is None:
            return None
        try:
            f = float(val)
            return None if (f != f) else f   # reject NaN
        except (TypeError, ValueError):
            return None


class NWPClient:
    CACHE_TTL = 3600

    async def fetch_model_forecast(
        self, model: str, latitude: float, longitude: float, forecast_hours: int = 48
    ) -> List[NWPForecastData]:
        om_model = NWP_MODEL_MAP.get(model.upper())
        if not om_model:
            return []

        # forecast_days = enough to cover forecast_hours from now
        forecast_days = max(2, (forecast_hours // 24) + 2)

        params = {
            "latitude":      latitude,
            "longitude":     longitude,
            "hourly":        ",".join(HOURLY_VARIABLES),
            "models":        om_model,
            "forecast_days": forecast_days,
            "timezone":      "UTC",
            "timeformat":    "iso8601",
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"{settings.open_meteo_base_url}/forecast", params=params
                )
            resp.raise_for_status()
            raw_data = resp.json()
            forecasts = self._parse(model, raw_data, forecast_hours)
            logger.info("nwp_fetched", model=model, points=len(forecasts),
                        lat=latitude, lon=longitude)
            return forecasts

        except Exception as e:
            logger.error("nwp_fetch_error", model=model, error=str(e))
            return []

    def _parse(self, model: str, data: dict, forecast_hours: int) -> List[NWPForecastData]:
        hourly = data.get("hourly", {})
        times  = hourly.get("time", [])
        now    = datetime.now(tz=timezone.utc)
        cutoff = now + timedelta(hours=forecast_hours)
        results = []

        for i, t_str in enumerate(times):
            try:
                # Open-Meteo returns "2026-10-01T18:00" (no Z) — add UTC
                if t_str.endswith("Z"):
                    valid_time = datetime.fromisoformat(t_str[:-1]).replace(tzinfo=timezone.utc)
                elif "+" in t_str:
                    valid_time = datetime.fromisoformat(t_str)
                else:
                    valid_time = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)

                # Only keep future times up to forecast_hours
                if valid_time < now - timedelta(minutes=30):
                    continue
                if valid_time > cutoff:
                    break

                row = {var: (hourly.get(var, [])[i] if i < len(hourly.get(var, [])) else None)
                       for var in HOURLY_VARIABLES}

                results.append(NWPForecastData(model, valid_time, row))
            except Exception as e:
                logger.debug("nwp_row_skip", i=i, error=str(e))
                continue

        return results

    async def fetch_all_models(
        self, latitude: float, longitude: float, forecast_hours: int = 48
    ) -> Dict[str, List[NWPForecastData]]:
        results = {}
        for model in ["GFS", "ECMWF", "JMA"]:
            forecasts = await self.fetch_model_forecast(model, latitude, longitude, forecast_hours)
            results[model] = forecasts
            status = "ok" if forecasts else "empty"
            logger.info("nwp_model_status", model=model, status=status, points=len(forecasts))
        return results
