import sys
from pathlib import Path
backend_dir = str(Path(__file__).parent.parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.models.base import BaseWeatherModel
__all__ = ["BaseWeatherModel"]
