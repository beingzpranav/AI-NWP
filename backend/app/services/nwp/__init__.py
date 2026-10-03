from app.services.nwp.client import NWPClient, NWPForecastData


def get_nwp_client() -> NWPClient:
    """Always return a fresh client (no singleton — avoids stale state)."""
    return NWPClient()
