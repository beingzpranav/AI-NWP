"""
Weather Union API Client — server-side only.
Uses get_weather_data endpoint with lat/lon (confirmed working).
API key NEVER exposed to frontend.
"""
from datetime import datetime, timezone
from typing import Any, Optional
import httpx
from app.core.config import get_settings
from app.core.cache import cache_get, cache_set
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

BASE_URL = "https://www.weatherunion.com/gw/weather/external/v0"


class WeatherUnionObservation:
    def __init__(self, raw: dict, station_id: str, station_name: str = ""):
        self.station_id   = station_id
        self.station_name = station_name
        self.fetched_at   = datetime.now(tz=timezone.utc)

        ld = raw.get("locality_weather_data") or {}

        self.temperature_c      = self._f(ld.get("temperature"))
        self.humidity_pct       = self._f(ld.get("humidity"))
        self.wind_speed_kmh     = self._f(ld.get("wind_speed"))
        self.wind_direction_deg = self._f(ld.get("wind_direction"))
        self.rain_intensity_mmph = self._f(ld.get("rain_intensity"))
        self.rain_accumulation_mm = self._f(ld.get("rain_accumulation"))
        self.is_valid = self.temperature_c is not None

    @staticmethod
    def _f(val: Any) -> Optional[float]:
        if val is None or val == "" or val == "NA":
            return None
        try:
            f = float(val)
            return None if (f != f) else f   # reject NaN only
        except (TypeError, ValueError):
            return None

    def to_dict(self) -> dict:
        return {
            "station_id":           self.station_id,
            "station_name":         self.station_name,
            "fetched_at":           self.fetched_at.isoformat(),
            "temperature_c":        self.temperature_c,
            "humidity_pct":         self.humidity_pct,
            "wind_speed_kmh":       self.wind_speed_kmh,
            "wind_direction_deg":   self.wind_direction_deg,
            "rain_intensity_mmph":  self.rain_intensity_mmph,
            "rain_accumulation_mm": self.rain_accumulation_mm,
            "is_valid":             self.is_valid,
        }


class WeatherUnionClient:
    """
    Fetches real-time weather from Weather Union using get_weather_data?lat&lon.
    Confirmed working endpoint (tested directly).
    API key is server-side only — never sent to frontend.
    """

    @property
    def is_configured(self) -> bool:
        return settings.weather_union_key_configured

    def _headers(self) -> dict:
        # Key stays server-side only
        return {"x-zomato-api-key": settings.weather_union_api_key}

    async def get_locality_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherUnionObservation]:
        if not self.is_configured:
            logger.warning("wu_not_configured")
            return None

        cache_key = f"wu:{latitude:.3f}:{longitude:.3f}"
        cached = await cache_get(cache_key)
        if cached:
            obs = WeatherUnionObservation.__new__(WeatherUnionObservation)
            obs.__dict__.update(cached)
            obs.fetched_at = datetime.fromisoformat(cached["fetched_at"])
            logger.debug("wu_cache_hit", key=cache_key)
            return obs

        url = f"{BASE_URL}/get_weather_data"
        params = {"latitude": latitude, "longitude": longitude}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers=self._headers(), params=params)

            logger.info("wu_http_status", status=resp.status_code, body=resp.text[:300])

            if resp.status_code == 401:
                logger.error("wu_auth_error", msg="Invalid API key — check WEATHER_UNION_API_KEY in .env")
                return None

            # WU returns 400 when lat/lon not in coverage but still sends data body
            # Always try to parse the response body
            try:
                data = resp.json()
            except Exception:
                logger.warning("wu_json_parse_fail", body=resp.text[:200])
                return None

            obs = WeatherUnionObservation(
                data,
                station_id=f"wu_{latitude:.3f}_{longitude:.3f}",
                station_name=data.get("message", f"{latitude:.2f},{longitude:.2f}"),
            )

            if obs.is_valid:
                await cache_set(cache_key, obs.to_dict(), ttl=settings.weather_union_cache_ttl_seconds)
                logger.info("wu_data_received",
                            lat=latitude, lon=longitude,
                            temp=obs.temperature_c,
                            humidity=obs.humidity_pct)
            else:
                logger.warning("wu_no_valid_data",
                               lat=latitude, lon=longitude,
                               raw_body=resp.text[:300])
            return obs

        except httpx.TimeoutException:
            logger.warning("wu_timeout", lat=latitude, lon=longitude)
            return None
        except Exception as e:
            logger.error("wu_exception", error=str(e))
            return None

    async def health_check(self) -> dict:
        return {"configured": self.is_configured, "base_url": BASE_URL}
