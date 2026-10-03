import sys
from pathlib import Path
backend_dir = str(Path(__file__).parent.parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.training.pipeline import (
    WeatherForecastingPipeline,
    chronological_split,
)

__all__ = ["WeatherForecastingPipeline", "chronological_split"]
