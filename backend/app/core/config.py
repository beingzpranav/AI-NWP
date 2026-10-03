"""
Central configuration — all settings loaded from environment variables.
No secrets are hardcoded here.
"""
from functools import lru_cache
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    try:
        from pydantic import BaseSettings
    except ImportError:
        class BaseSettings:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
    class SettingsConfigDict:
        def __init__(self, **kwargs):
            pass

from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    # ── App ─────────────────────────────────────────────────
    app_name: str = "Weather AI Platform"
    environment: str = "development"
    debug: bool = False
    backend_port: int = 8000
    secret_key: str = "change-me"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Weather Union ────────────────────────────────────────
    # The API key MUST be set in the .env file on the server.
    # It is NEVER sent to the frontend.
    weather_union_api_key: str = "PASTE WEATHER UNION API KEY"
    weather_union_base_url: str = "https://www.weatherunion.com/gw/weather/external/v0"
    weather_union_cache_ttl_seconds: int = 300   # 5 min cache
    weather_union_timeout_seconds: int = 10
    weather_union_max_retries: int = 3

    # ── NWP (Open-Meteo proxy — no key required) ─────────────
    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://weather_user:weather_pass@localhost:5432/weather_ai_db"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── ML ───────────────────────────────────────────────────
    model_artifact_dir: str = "./artifacts"
    training_data_dir: str = "./data/training"
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def weather_union_key_configured(self) -> bool:
        """Returns True if a real API key has been provided."""
        return (
            self.weather_union_api_key != "PASTE WEATHER UNION API KEY"
            and len(self.weather_union_api_key) > 10
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
