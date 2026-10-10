"""Configuration constants for USDA FoodData Central matching."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Ensure .env is loaded if data.usda is used independently of main.py
    _project_root = Path(__file__).resolve().parents[2]
    _env_path = _project_root / ".env"
    if _env_path.is_file():
        load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass


USDA_API_KEY_ENV = "USDA_API_KEY"
DEFAULT_USDA_API_KEY = ""
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

CONFIDENCE_THRESHOLD = 0.70
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RATE_LIMIT = 0.25
RETRY_BACKOFF = 0.5
SEARCH_PAGE_SIZE = 25

PREFERRED_DATA_TYPES = (
    "Foundation",
    "SR Legacy",
    "Survey (FNDDS)",
)
