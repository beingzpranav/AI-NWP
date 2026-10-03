import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app

app = app
