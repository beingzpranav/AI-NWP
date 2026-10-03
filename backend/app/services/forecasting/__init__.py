from app.services.forecasting.engine import ForecastingEngine

_engine: ForecastingEngine = None


def get_forecasting_engine() -> ForecastingEngine:
    global _engine
    if _engine is None:
        _engine = ForecastingEngine()
    return _engine
