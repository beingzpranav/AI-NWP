"""
Structured logging configuration using structlog.
API keys and credentials are explicitly excluded from log context.
"""
import logging
import sys

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

from app.core.config import get_settings


SENSITIVE_KEYS = {
    "weather_union_api_key", "api_key", "password", "secret",
    "token", "authorization", "x-api-key",
}


def _censor_sensitive(_, __, event_dict: dict) -> dict:
    """Strip sensitive fields before logging."""
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in SENSITIVE_KEYS):
            event_dict[key] = "***REDACTED***"
    return event_dict


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    if HAS_STRUCTLOG:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                _censor_sensitive,
                structlog.dev.ConsoleRenderer() if settings.debug
                else structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        level=level,
    )


class FallbackLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def info(self, msg, **kwargs):
        ctx = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.info(f"{msg} {ctx}".strip())

    def warning(self, msg, **kwargs):
        ctx = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.warning(f"{msg} {ctx}".strip())

    def error(self, msg, **kwargs):
        ctx = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.error(f"{msg} {ctx}".strip())

    def debug(self, msg, **kwargs):
        ctx = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.debug(f"{msg} {ctx}".strip())


def get_logger(name: str):
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return FallbackLogger(name)
