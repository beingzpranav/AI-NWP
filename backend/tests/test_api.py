"""
API endpoint tests.
Tests health, forecast, weather-union status, and model weight endpoints.
Verifies that the API key is NEVER returned in any response.
"""
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_health_returns_ok(async_client):
    resp = await async_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "environment" in data
    # API key must never appear
    assert "api_key" not in str(data).lower()
    assert "weather_union_api_key" not in str(data).lower()


@pytest.mark.asyncio
async def test_health_has_wu_configured_flag(async_client):
    resp = await async_client.get("/api/health")
    data = resp.json()
    assert "weather_union_configured" in data
    # Value is a boolean
    assert isinstance(data["weather_union_configured"], bool)


@pytest.mark.asyncio
async def test_forecast_returns_structure(async_client):
    resp = await async_client.get(
        "/api/forecast/", params={"lat": 28.6139, "lon": 77.2090, "hours": 24}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert "location" in data
    assert "generated_at" in data
    assert "data_sources" in data
    assert len(data["points"]) > 0


@pytest.mark.asyncio
async def test_forecast_point_structure(async_client):
    resp = await async_client.get(
        "/api/forecast/", params={"lat": 12.9716, "lon": 77.5946, "hours": 6}
    )
    assert resp.status_code == 200
    data = resp.json()
    point = data["points"][0]
    assert "valid_time" in point
    assert "horizon_hours" in point
    # Should have at least one weather variable
    has_weather = any(
        point.get(k) is not None
        for k in ["temperature_c", "humidity_pct", "wind_speed_kmh"]
    )
    assert has_weather


@pytest.mark.asyncio
async def test_forecast_no_api_key_in_response(async_client):
    resp = await async_client.get(
        "/api/forecast/", params={"lat": 28.6139, "lon": 77.2090, "hours": 6}
    )
    raw = resp.text.lower()
    # The Weather Union API key must NEVER appear in any response
    assert "paste weather union api key" not in raw
    assert "x-zomato-api-key" not in raw
    assert "weather_union_api_key" not in raw


@pytest.mark.asyncio
async def test_weather_current_returns_data(async_client):
    resp = await async_client.get(
        "/api/weather/current", params={"lat": 28.6139, "lon": 77.2090}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "location" in data
    assert "observed_at" in data
    assert "source" in data


@pytest.mark.asyncio
async def test_wu_status_no_key_exposed(async_client):
    resp = await async_client.get("/api/weather/weather-union/status")
    assert resp.status_code == 200
    raw = resp.text.lower()
    assert "api_key" not in raw
    assert "x-zomato" not in raw
    data = resp.json()
    assert "configured" in data
    assert "connected" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_model_weights_returns_valid_structure(async_client):
    resp = await async_client.get("/api/models/weights")
    assert resp.status_code == 200
    data = resp.json()
    assert "weights" in data
    weights = data["weights"]
    assert isinstance(weights, dict)
    total = sum(float(v) for v in weights.values())
    # Weights must sum to ~1.0
    assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected 1.0"


@pytest.mark.asyncio
async def test_locations_endpoint(async_client):
    resp = await async_client.get("/api/locations/")
    # Returns list (may be empty if DB not seeded in test)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_invalid_coordinates_rejected(async_client):
    resp = await async_client.get(
        "/api/forecast/", params={"lat": 999.0, "lon": 77.0, "hours": 6}
    )
    assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_location_not_found(async_client):
    resp = await async_client.get("/api/forecast/99999")
    assert resp.status_code in (404, 500)
