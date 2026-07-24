"""Configuration constants for USDA FoodData Central matching."""

from __future__ import annotations


USDA_API_KEY_ENV = "USDA_API_KEY"
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
