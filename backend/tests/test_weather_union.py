"""Tests for Weather Union client (mocked HTTP)."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.weather_union.client import WeatherUnionClient, WeatherUnionObservation


def make_mock_response(data: dict, status: int = 200):
    mock = AsyncMock()
    mock.status_code = status
    mock.json.return_value = data
    mock.text = str(data)
    return mock


@pytest.mark.asyncio
async def test_observation_parsing():
    raw = {
        "locality_weather_data": {
            "temperature": "32.5",
            "humidity": "65",
            "wind_speed": "12.3",
            "wind_direction": "220",
            "rain_intensity": "0.0",
            "rain_accumulation": "2.1",
        },
        "model_based": False,
    }
    obs = WeatherUnionObservation(raw, "test_station", "Test")
    assert obs.temperature_c == pytest.approx(32.5)
    assert obs.humidity_pct == pytest.approx(65.0)
    assert obs.wind_speed_kmh == pytest.approx(12.3)
    assert obs.is_valid is True


@pytest.mark.asyncio
async def test_observation_missing_values():
    raw = {
        "locality_weather_data": {
            "temperature": None,
            "humidity": "NA",
            "wind_speed": "",
        }
    }
    obs = WeatherUnionObservation(raw, "station_x")
    assert obs.temperature_c is None
    assert obs.humidity_pct is None
    assert obs.wind_speed_kmh is None
    assert obs.is_valid is False  # all key fields null


@pytest.mark.asyncio
async def test_client_not_configured_returns_none():
    """When API key is not set, client returns None gracefully."""
    client = WeatherUnionClient()
    # Patch is_configured to return False
    with patch.object(type(client), "is_configured", new_callable=lambda: property(lambda self: False)):
        result = await client.get_locality_weather(28.6, 77.2)
    assert result is None


@pytest.mark.asyncio
async def test_health_check_does_not_expose_key():
    client = WeatherUnionClient()
    health = await client.health_check()
    # Key should NOT appear in health response
    assert "api_key" not in str(health).lower()
    assert "x-zomato" not in str(health).lower()
