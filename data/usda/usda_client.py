"""Small USDA FoodData Central search client."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

try:
    from .config import (
        MAX_RETRIES,
        PREFERRED_DATA_TYPES,
        RATE_LIMIT,
        REQUEST_TIMEOUT,
        RETRY_BACKOFF,
        SEARCH_PAGE_SIZE,
        DEFAULT_USDA_API_KEY,
        USDA_API_KEY_ENV,
        USDA_SEARCH_URL,
    )
except ImportError:
    from config import (
        MAX_RETRIES,
        PREFERRED_DATA_TYPES,
        RATE_LIMIT,
        REQUEST_TIMEOUT,
        RETRY_BACKOFF,
        SEARCH_PAGE_SIZE,
        DEFAULT_USDA_API_KEY,
        USDA_API_KEY_ENV,
        USDA_SEARCH_URL,
    )


class _USDAClient:
    """Reusable client exposing only the USDA search endpoint."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self.session = requests.Session()
        self.last_request_at = 0.0

    @property
    def api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key
        return os.environ.get(USDA_API_KEY_ENV, DEFAULT_USDA_API_KEY)

    @api_key.setter
    def api_key(self, value: str | None) -> None:
        self._api_key = value

    def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self.last_request_at

        if elapsed < RATE_LIMIT:
            time.sleep(RATE_LIMIT - elapsed)

        self.last_request_at = time.monotonic()

    def search_food(self, query: str) -> dict[str, Any]:
        """Search USDA FoodData Central and return parsed JSON."""

        query = query.strip()

        if not query:
            return {"foods": []}

        if not self.api_key:
            return {
                "foods": [],
                "error": f"Missing {USDA_API_KEY_ENV} environment variable",
            }

        params: dict[str, Any] = {
        "api_key": self.api_key,
        "query": query,
        "pageSize": SEARCH_PAGE_SIZE,
    }

        for attempt in range(MAX_RETRIES + 1):
            self._wait_for_rate_limit()

            try:
                response = self.session.get(
                    USDA_SEARCH_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                if response.status_code == 429 or response.status_code >= 500:
                    raise requests.HTTPError(
                        f"USDA search failed with status {response.status_code}",
                        response=response,
                    )

                response.raise_for_status()
                data = response.json()
                preferred = set(PREFERRED_DATA_TYPES)

                foods = data.get("foods", [])

                filtered = [
                    food
                    for food in foods
                    if food.get("dataType") in preferred
                ]

                # Use filtered results if any exist; otherwise keep the originals.
                if filtered:
                    data["foods"] = filtered
                                

                if isinstance(data, dict):
                    return data

                return {"foods": [], "error": "USDA returned an unexpected response"}

            except (requests.RequestException, ValueError) as exc:
                if attempt >= MAX_RETRIES:
                    error_msg = str(exc)
                    if self.api_key and self.api_key in error_msg:
                        error_msg = error_msg.replace(self.api_key, "[REDACTED]")
                    return {"foods": [], "error": error_msg}

                time.sleep(RETRY_BACKOFF * (attempt + 1))

        return {"foods": []}


_CLIENT = _USDAClient()


def search_food(query: str) -> dict[str, Any]:
    """Search USDA FoodData Central for a food name."""

    return _CLIENT.search_food(query)


__all__ = ["search_food"]
