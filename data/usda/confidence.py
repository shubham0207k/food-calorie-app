"""Confidence scoring for USDA FoodData Central candidates."""

from __future__ import annotations

import re
from typing import Any

try:
    from .config import PREFERRED_DATA_TYPES
except ImportError:
    from config import PREFERRED_DATA_TYPES


EXACT_MATCH_WEIGHT = 0.50
NORMALIZED_NAME_WEIGHT = 0.20
ALIAS_MATCH_WEIGHT = 0.15
WORD_SIMILARITY_WEIGHT = 0.10
PREFERRED_DATA_TYPE_WEIGHT = 0.05


def normalize_name(value: Any) -> str:
    """Normalize a food name for conservative text comparison."""

    if not isinstance(value, str):
        return ""

    text = value.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _singularize(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return f"{word[:-3]}y"

    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]

    return word


def _tokens(value: Any) -> list[str]:
    return [
        _singularize(word)
        for word in normalize_name(value).split()
    ]


def _token_text(value: Any) -> str:
    return " ".join(_tokens(value))


def _first_phrase(value: str) -> str:
    return re.split(r"[,;:/(]", value, maxsplit=1)[0]

def _candidate_description(candidate: dict[str, Any]) -> str:
    description = candidate.get("description")

    if isinstance(description, str):
        return description

    return ""


def _candidate_data_type(candidate: dict[str, Any]) -> str:
    data_type = candidate.get("dataType", candidate.get("data_type"))

    if isinstance(data_type, str):
        return data_type

    return ""


def _contains_phrase(needle: str, haystack: str) -> bool:
    return f" {needle} " in f" {haystack} "


def word_similarity(name: str, candidate_name: str) -> float:
    """Return word overlap from 0.00 to 1.00."""

    name_words = set(_tokens(name))
    candidate_words = set(_tokens(candidate_name))

    if not name_words or not candidate_words:
        return 0.0

    return len(name_words & candidate_words) / len(name_words)


def _is_exact_match(name: str, description: str) -> bool:
    name_text = _token_text(name)

    if not name_text:
        return False

    return name_text in {
        _token_text(description),
        _token_text(_first_phrase(description)),
    }


def _has_normalized_name_match(name: str, description: str) -> bool:
    name_text = _token_text(name)
    description_text = _token_text(description)

    if not name_text or not description_text:
        return False

    return (
        name_text == description_text
        or _contains_phrase(name_text, description_text)
        or _contains_phrase(description_text, name_text)
    )


def _has_alias_match(
    aliases: list[str],
    matched_query: str | None,
    description: str,
) -> bool:
    description_text = _token_text(description)
    first_phrase_text = _token_text(_first_phrase(description))

    for alias in aliases:
        alias_text = _token_text(alias)

        if not alias_text:
            continue

        if alias_text in {description_text, first_phrase_text}:
            return True

        if _contains_phrase(alias_text, description_text):
            return True

        if (
            matched_query
            and alias_text == _token_text(matched_query)
            and word_similarity(alias, description) >= 0.8
        ):
            return True

    return False


def score_candidate(
    candidate: dict[str, Any],
    display_name: str,
    aliases: list[str] | None = None,
    matched_query: str | None = None,
) -> float:
    """Score one USDA search candidate from 0.00 to 1.00."""

    aliases = aliases or []
    description = _candidate_description(candidate)

    if not description:
        return 0.0

    score = 0.0
    query_name = matched_query or display_name
    scored_names = [display_name]

    if matched_query and _token_text(matched_query) != _token_text(display_name):
        scored_names.append(matched_query)

    if any(_is_exact_match(name, description) for name in scored_names):
        score += EXACT_MATCH_WEIGHT

    if any(_has_normalized_name_match(name, description) for name in scored_names):
        score += NORMALIZED_NAME_WEIGHT

    if _has_alias_match(aliases, matched_query, description):
        score += ALIAS_MATCH_WEIGHT

    score += word_similarity(query_name, description) * WORD_SIMILARITY_WEIGHT

    if _candidate_data_type(candidate) in PREFERRED_DATA_TYPES:
        score += PREFERRED_DATA_TYPE_WEIGHT

    return min(round(score, 4), 1.0)
