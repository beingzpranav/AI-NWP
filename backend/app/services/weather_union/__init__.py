from app.services.weather_union.client import WeatherUnionClient, WeatherUnionObservation


def get_weather_union_client() -> WeatherUnionClient:
    """Always return a fresh client."""
    return WeatherUnionClient()
