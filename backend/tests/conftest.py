"""
Shared pytest fixtures for backend tests.
Uses an in-memory SQLite database so tests run without PostgreSQL.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import get_settings


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture
def mock_wu_client():
    """Weather Union client that returns a fake observation."""
    from app.services.weather_union.client import WeatherUnionObservation
    obs = WeatherUnionObservation.__new__(WeatherUnionObservation)
    obs.station_id = "test_station"
    obs.station_name = "Test Station"
    obs.temperature_c = 32.5
    obs.humidity_pct = 65.0
    obs.wind_speed_kmh = 12.0
    obs.wind_direction_deg = 220.0
    obs.rain_intensity_mmph = 0.0
    obs.rain_accumulation_mm = 1.2
    obs.model_based = False
    obs.is_valid = True
    from datetime import datetime, timezone
    obs.fetched_at = datetime.now(tz=timezone.utc)

    client = AsyncMock()
    client.is_configured = True
    client.get_locality_weather = AsyncMock(return_value=obs)
    client.get_station_weather = AsyncMock(return_value=obs)
    client.health_check = AsyncMock(return_value={"configured": True, "base_url": "https://example.com"})
    return client


@pytest.fixture
def mock_nwp_client():
    """NWP client that returns fake forecast data."""
    from app.services.nwp.client import NWPForecastData
    from datetime import datetime, timezone, timedelta

    now = datetime.now(tz=timezone.utc)

    def make_point(model, h):
        f = NWPForecastData.__new__(NWPForecastData)
        f.model = model
        f.run_time = now
        f.valid_time = now + timedelta(hours=h)
        f.horizon_hours = h
        f.temperature_c = 28.0 + h * 0.1
        f.humidity_pct = 65.0
        f.wind_speed_kmh = 12.0
        f.wind_direction_deg = 220.0
        f.precipitation_mm = 0.5
        f.pressure_hpa = 1013.0
        f.cloud_cover_pct = 40.0
        return f

    client = AsyncMock()
    client.fetch_model_forecast = AsyncMock(
        side_effect=lambda model, lat, lon, forecast_hours=48: [
            make_point(model, h) for h in range(min(forecast_hours, 48))
        ]
    )
    client.fetch_all_models = AsyncMock(
        return_value={
            "GFS":   [make_point("GFS",   h) for h in range(48)],
            "ECMWF": [make_point("ECMWF", h) for h in range(48)],
            "JMA":   [make_point("JMA",   h) for h in range(48)],
        }
    )
    return client


@pytest_asyncio.fixture
async def async_client(mock_wu_client, mock_nwp_client):
    """HTTP test client with mocked external services."""
    with patch("app.services.weather_union.get_weather_union_client",
               return_value=mock_wu_client), \
         patch("app.services.nwp.get_nwp_client",
               return_value=mock_nwp_client):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            yield client
