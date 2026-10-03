import sys
from pathlib import Path

# Add project root and backend directory to sys.path so modules import seamlessly on Vercel
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.main import app

# Vercel Serverless Function entry point
app = app
