"""
Vercel Serverless Function Entrypoint for FastAPI.
Exposes the FastAPI 'app' instance with the repository root added to sys.path.
"""

import sys
from pathlib import Path

# Add project root directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app  # noqa: F401
