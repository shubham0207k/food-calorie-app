"""USDA matching pipeline for FoodVision food records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .confidence import score_candidate
    from .config import CONFIDENCE_THRESHOLD
    from .usda_client import search_food
except ImportError:
    from confidence import score_candidate
    from config import CONFIDENCE_THRESHOLD
    from usda_client import search_food


@dataclass(frozen=True)
class MatchResult:
    """Result of matching one FoodVision food to USDA."""

    status: str
    usda: dict[str, Any] | None = None
    confidence: float = 0.0
    query: str = ""
    warning: str | None = None


def has_existing_usda(value: Any) -> bool:
    """Return whether a food already has a USDA value."""

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, dict):
        return bool(value)

    return False


def _food_aliases(food: dict[str, Any]) -> list[str]:
    aliases = food.get("aliases")

    if not isinstance(aliases, list):
        return []

    return [
        alias
        for alias in aliases
        if isinstance(alias, str) and alias.strip()
    ]


def _candidate_fdc_id(candidate: dict[str, Any]) -> int | None:
    fdc_id = candidate.get("fdcId", candidate.get("fdc_id"))

    if isinstance(fdc_id, bool):
        return None

    if isinstance(fdc_id, int):
        return fdc_id

    if isinstance(fdc_id, str) and fdc_id.isdigit():
        return int(fdc_id)

    return None


def _candidate_description(candidate: dict[str, Any]) -> str:
    description = candidate.get("description")

    if isinstance(description, str):
        return description.strip()

    return ""


def _candidate_data_type(candidate: dict[str, Any]) -> str:
    data_type = candidate.get("dataType", candidate.get("data_type"))

    if isinstance(data_type, str):
        return data_type.strip()

    return ""


def _usda_field(candidate: dict[str, Any], confidence: float) -> dict[str, Any] | None:
    fdc_id = _candidate_fdc_id(candidate)
    description = _candidate_description(candidate)
    data_type = _candidate_data_type(candidate)

    if fdc_id is None or not description:
        return None

    return {
        "fdc_id": fdc_id,
        "description": description,
        "data_type": data_type,
        "confidence": round(confidence, 2),
    }


def _search_candidates(query: str) -> tuple[list[dict[str, Any]], str | None]:
    data = search_food(query)
    foods = data.get("foods", [])
    warning = data.get("error")

    if not isinstance(foods, list):
        return [], warning or "USDA search response did not contain a foods list"

    candidates = [
        food
        for food in foods
        if isinstance(food, dict)
    ]

    return candidates, warning if isinstance(warning, str) else None


def _candidate_key(candidate: dict[str, Any]) -> tuple[Any, str]:
    return (
        candidate.get("fdcId", candidate.get("fdc_id")),
        _candidate_description(candidate).casefold(),
    )


def _best_candidate(
    candidates: list[dict[str, Any]],
    display_name: str,
    aliases: list[str],
    query: str,
) -> tuple[dict[str, Any] | None, float]:
    best_candidate = None
    best_confidence = 0.0

    for candidate in candidates:
        confidence = score_candidate(
            candidate=candidate,
            display_name=display_name,
            aliases=aliases,
            matched_query=query,
        )

        if confidence > best_confidence:
            best_candidate = candidate
            best_confidence = confidence

    return best_candidate, best_confidence


def match_food(
    food: dict[str, Any],
    min_confidence: float = CONFIDENCE_THRESHOLD,
) -> MatchResult:
    """Match one FoodVision food to the best USDA search candidate."""

    display_name = food.get("display_name")

    if not isinstance(display_name, str) or not display_name.strip():
        return MatchResult(
            status="skipped",
            warning="Food record is missing display_name",
        )

    display_name = display_name.strip()
    aliases = _food_aliases(food)
    seen_candidates: set[tuple[Any, str]] = set()
    all_candidates: list[dict[str, Any]] = []
    warnings: list[str] = []

    candidates, warning = _search_candidates(display_name)

    if warning:
        warnings.append(warning)

    for candidate in candidates:
        key = _candidate_key(candidate)

        if key not in seen_candidates:
            seen_candidates.add(key)
            all_candidates.append(candidate)

    best_candidate, best_confidence = _best_candidate(
        candidates=all_candidates,
        display_name=display_name,
        aliases=aliases,
        query=display_name,
    )
    best_query = display_name

    if best_confidence < min_confidence:
        for alias in aliases:
            alias_candidates, warning = _search_candidates(alias)

            if warning:
                warnings.append(warning)

            for candidate in alias_candidates:
                key = _candidate_key(candidate)

                if key not in seen_candidates:
                    seen_candidates.add(key)
                    all_candidates.append(candidate)

            candidate, confidence = _best_candidate(
                candidates=all_candidates,
                display_name=display_name,
                aliases=aliases,
                query=alias,
            )

            if confidence > best_confidence:
                best_candidate = candidate
                best_confidence = confidence
                best_query = alias

    if best_candidate is None or best_confidence < min_confidence:
        return MatchResult(
            status="unmatched",
            confidence=round(best_confidence, 2),
            query=best_query,
            warning=warnings[0] if warnings else None,
        )

    usda = _usda_field(best_candidate, best_confidence)

    if usda is None:
        return MatchResult(
            status="unmatched",
            confidence=round(best_confidence, 2),
            query=best_query,
            warning="Best USDA candidate did not include fdcId or description",
        )

    return MatchResult(
        status="matched",
        usda=usda,
        confidence=usda["confidence"],
        query=best_query,
        warning=warnings[0] if warnings else None,
    )
