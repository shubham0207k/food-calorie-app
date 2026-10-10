"""USDA matching pipeline for FoodVision food records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from .confidence import normalize_name, score_candidate
    from .config import CONFIDENCE_THRESHOLD, PREFERRED_DATA_TYPES
    from .usda_client import search_food
except ImportError:
    from confidence import normalize_name, score_candidate
    from config import CONFIDENCE_THRESHOLD, PREFERRED_DATA_TYPES
    from usda_client import search_food


@dataclass(frozen=True)
class MatchResult:
    """Result of matching one FoodVision food to USDA."""

    status: str
    usda: dict[str, Any] | None = None
    confidence: float = 0.0
    query: str = ""
    warning: str | None = None


DATA_TYPE_CONFIDENCE_MARGIN = 0.03

USDA_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "burger": ("hamburger",),
    "cup cakes": ("cupcakes",),
    "donuts": ("doughnuts",),
    "french fries": ("french fried potatoes",),
    "fries": ("french fries", "french fried potatoes"),
    "hot dog": ("frankfurter",),
    "mac and cheese": ("macaroni and cheese",),
    "omelette": ("omelet",),
    "steak": ("beef steak",),
}

TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "in",
    "of",
    "or",
    "the",
    "with",
}

DATA_TYPE_PRIORITY = {
    data_type: index
    for index, data_type in enumerate(PREFERRED_DATA_TYPES)
}


def has_existing_usda(value: Any) -> bool:
    """Return whether a food already has a USDA value."""

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, dict):
        return bool(value)

    return False


def _normalize_search_term(value: str) -> str:
    return " ".join(value.lower().split())


def _usda_search_aliases(value: str) -> list[str]:
    return list(USDA_SEARCH_ALIASES.get(_normalize_search_term(value), ()))


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


def _candidate_data_type_priority(candidate: dict[str, Any]) -> int:
    return DATA_TYPE_PRIORITY.get(
        _candidate_data_type(candidate),
        len(DATA_TYPE_PRIORITY),
    )


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
    data = search_food(_normalize_search_term(query))
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


def _singularize_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"

    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]

    return token


def _meaningful_tokens(value: str) -> set[str]:
    return {
        _singularize_token(token)
        for token in normalize_name(value).split()
        if token not in TOKEN_STOPWORDS
    }


def _is_clear_mismatch(
    candidate: dict[str, Any],
    display_name: str,
    aliases: list[str],
    matched_query: str,
) -> bool:
    description_tokens = _meaningful_tokens(_candidate_description(candidate))

    if not description_tokens:
        return True

    names = [display_name, matched_query, *aliases]

    for name in names:
        name_tokens = _meaningful_tokens(name)

        if not name_tokens:
            continue

        if len(name_tokens) == 1 and name_tokens & description_tokens:
            return False

        if len(name_tokens) > 1 and name_tokens <= description_tokens:
            return False

    return True


def _candidate_key(candidate: dict[str, Any]) -> tuple[Any, str]:
    return (
        candidate.get("fdcId", candidate.get("fdc_id")),
        _candidate_description(candidate).casefold(),
    )


def _is_better_candidate(
    candidate: dict[str, Any],
    confidence: float,
    best_candidate: dict[str, Any] | None,
    best_confidence: float,
    min_confidence: float,
) -> bool:
    if best_candidate is None:
        return True

    if confidence > best_confidence + DATA_TYPE_CONFIDENCE_MARGIN:
        return True

    if best_confidence > confidence + DATA_TYPE_CONFIDENCE_MARGIN:
        return False

    candidate_accepted = confidence >= min_confidence
    best_accepted = best_confidence >= min_confidence

    if candidate_accepted != best_accepted:
        return candidate_accepted

    candidate_priority = _candidate_data_type_priority(candidate)
    best_priority = _candidate_data_type_priority(best_candidate)

    if candidate_priority != best_priority:
        return candidate_priority < best_priority

    return confidence > best_confidence


def _best_candidate(
    candidate_matches: list[tuple[dict[str, Any], str]],
    display_name: str,
    aliases: list[str],
    min_confidence: float,
) -> tuple[dict[str, Any] | None, float, str]:
    best_candidate = None
    best_confidence = 0.0
    best_query = ""

    for candidate, query in candidate_matches:
        if _is_clear_mismatch(candidate, display_name, aliases, query):
            continue

        confidence = score_candidate(
            candidate=candidate,
            display_name=display_name,
            aliases=aliases,
            matched_query=query,
        )

        if _is_better_candidate(
            candidate=candidate,
            confidence=confidence,
            best_candidate=best_candidate,
            best_confidence=best_confidence,
            min_confidence=min_confidence,
        ):
            best_candidate = candidate
            best_confidence = confidence
            best_query = query

    return best_candidate, best_confidence, best_query


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
    usda_aliases = _usda_search_aliases(display_name)
    scoring_aliases = [*aliases, *usda_aliases]
    seen_candidate_queries: set[tuple[tuple[Any, str], str]] = set()
    seen_queries: set[str] = set()
    candidate_matches: list[tuple[dict[str, Any], str]] = []
    warnings: list[str] = []

    def add_search_results(raw_query: str) -> None:
        query = _normalize_search_term(raw_query)

        if not query or query in seen_queries:
            return

        seen_queries.add(query)
        candidates, warning = _search_candidates(query)

        if warning:
            warnings.append(warning)

        for candidate in candidates:
            candidate_query_key = (_candidate_key(candidate), query)

            if candidate_query_key not in seen_candidate_queries:
                seen_candidate_queries.add(candidate_query_key)
                candidate_matches.append((candidate, query))

    add_search_results(display_name)

    for alias in usda_aliases:
        add_search_results(alias)

    best_candidate, best_confidence, best_query = _best_candidate(
        candidate_matches=candidate_matches,
        display_name=display_name,
        aliases=scoring_aliases,
        min_confidence=min_confidence,
    )

    if best_confidence < min_confidence:
        for alias in aliases:
            add_search_results(alias)

            for usda_alias in _usda_search_aliases(alias):
                add_search_results(usda_alias)

            candidate, confidence, query = _best_candidate(
                candidate_matches=candidate_matches,
                display_name=display_name,
                aliases=scoring_aliases,
                min_confidence=min_confidence,
            )

            if candidate is not None:
                best_candidate = candidate
                best_confidence = confidence
                best_query = query

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
