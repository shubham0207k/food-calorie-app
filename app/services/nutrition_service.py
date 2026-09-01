"""Nutrition lookup and calculation helpers for FoodVision AI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from data.usda.confidence import normalize_name
from data.usda.matcher import match_food
from data.usda.usda_client import search_food


SOURCE_USDA = "USDA FoodData Central"
SOURCE_LOCAL = "FoodVision local data"
UNKNOWN = "Unknown"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "knowledge_base"

NUTRIENTS = {
    "calories": ({1008}, {"energy"}),
    "protein": ({1003}, {"protein"}),
    "fat": ({1004}, {"total lipid fat", "total fat"}),
    "carbohydrates": ({1005}, {"carbohydrate by difference", "carbohydrate"}),
}


def unavailable_nutrition(
    food_name: str | None,
    warning: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    response = {
        "food_name": _clean_name(food_name),
        "nutrition_available": False,
        "calories": None,
        "protein": None,
        "fat": None,
        "carbohydrates": None,
        "serving_size": None,
        "serving_unit": None,
        "source": None,
        "confidence": confidence,
        "usda": None,
    }

    if warning:
        response["warning"] = warning

    return response


def normalize_nutrition_response(
    food_name: str,
    raw_nutrition: dict[str, Any] | None,
    source: str = SOURCE_USDA,
    confidence: float | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    """Normalize legacy nutrition data or one USDA search result."""

    if not isinstance(raw_nutrition, dict):
        return unavailable_nutrition(food_name, warning, confidence)

    if isinstance(raw_nutrition.get("foodNutrients"), list):
        return nutrition_from_usda_food(raw_nutrition, food_name, confidence, warning)

    serving_size = _number(raw_nutrition.get("serving_size"))
    serving_unit = raw_nutrition.get("serving_unit")

    if serving_size is None:
        serving_size, serving_unit = _parse_serving(raw_nutrition.get("serving"))

    nutrition = {
        "food_name": _clean_name(food_name),
        "nutrition_available": False,
        "calories": _number(raw_nutrition.get("calories")),
        "protein": _number(raw_nutrition.get("protein")),
        "fat": _number(raw_nutrition.get("fat")),
        "carbohydrates": _number(
            raw_nutrition.get("carbohydrates", raw_nutrition.get("carbs"))
        ),
        "serving_size": serving_size,
        "serving_unit": str(serving_unit).strip() if serving_unit else None,
        "source": None,
        "confidence": confidence,
        "usda": raw_nutrition.get("usda"),
    }
    nutrition["nutrition_available"] = _has_macros(nutrition)
    nutrition["source"] = source if nutrition["nutrition_available"] else None

    if warning:
        nutrition["warning"] = warning

    return nutrition


def nutrition_from_usda_food(
    food: dict[str, Any],
    food_name: str | None = None,
    confidence: float | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    """Build a standard nutrition payload from a USDA search result."""

    if not isinstance(food, dict):
        return unavailable_nutrition(food_name, warning, confidence)

    serving_size = _number(food.get("servingSize"))
    serving_unit = food.get("servingSizeUnit")

    if serving_size is None:
        serving_size, serving_unit = _parse_serving(food.get("householdServingFullText"))

    nutrition = {
        "food_name": _clean_name(food_name or food.get("description")),
        "nutrition_available": False,
        "calories": _food_nutrient(food, "calories"),
        "protein": _food_nutrient(food, "protein"),
        "fat": _food_nutrient(food, "fat"),
        "carbohydrates": _food_nutrient(food, "carbohydrates"),
        "serving_size": serving_size or 100.0,
        "serving_unit": str(serving_unit or "g").strip().lower(),
        "source": None,
        "confidence": confidence,
        "usda": _usda_metadata(food, confidence),
    }
    nutrition["nutrition_available"] = _has_macros(nutrition)
    nutrition["source"] = SOURCE_USDA if nutrition["nutrition_available"] else None

    if warning:
        nutrition["warning"] = warning

    return nutrition


def get_nutrition(
    food_name: str,
    search_func: Callable[[str], dict[str, Any]] = search_food,
    matcher_func: Callable[..., Any] = match_food,
) -> dict[str, Any]:
    """Resolve a food name, query USDA, and return standard nutrition data."""

    if not isinstance(food_name, str) or not food_name.strip():
        return unavailable_nutrition(food_name)

    display_name, query, aliases, usda = _resolve_food(food_name)
    confidence = _mapping_confidence(usda)
    warning = None

    if not usda:
        try:
            match = matcher_func({"display_name": display_name, "aliases": aliases})
            warning = getattr(match, "warning", None)
            confidence = getattr(match, "confidence", confidence)

            if getattr(match, "status", None) == "matched" and getattr(match, "usda", None):
                usda = match.usda
                query = usda.get("description") or getattr(match, "query", query)
        except Exception as exc:
            warning = str(exc)

    try:
        data = search_func(query)
    except Exception as exc:
        return unavailable_nutrition(display_name, str(exc), confidence)

    if not isinstance(data, dict):
        return unavailable_nutrition(
            display_name,
            "USDA search response was not a dictionary",
            confidence,
        )

    selected_food = _select_usda_food(data.get("foods"), usda)
    warning = data.get("error") or warning

    if selected_food is None:
        return unavailable_nutrition(display_name, warning, confidence)

    return nutrition_from_usda_food(selected_food, display_name, confidence, warning)


def to_legacy_nutrition(nutrition: dict[str, Any] | None) -> dict[str, Any]:
    """Convert standard nutrition data to the existing API response shape."""

    if not isinstance(nutrition, dict) or not nutrition.get("nutrition_available"):
        return legacy_unknown_nutrition()

    return {
        "calories": _value_or_unknown(nutrition.get("calories")),
        "serving": _format_serving(
            nutrition.get("serving_size"),
            nutrition.get("serving_unit"),
        ),
        "protein": _value_or_unknown(nutrition.get("protein")),
        "carbs": _value_or_unknown(nutrition.get("carbohydrates")),
        "fat": _value_or_unknown(nutrition.get("fat")),
    }


def legacy_unknown_nutrition() -> dict[str, Any]:
    return {
        "calories": UNKNOWN,
        "serving": UNKNOWN,
        "protein": UNKNOWN,
        "carbs": UNKNOWN,
        "fat": UNKNOWN,
    }


def calculate_nutrition_for_grams(
    nutrition: dict[str, Any],
    grams: float,
) -> dict[str, Any]:
    """Scale per-serving nutrition values to a requested gram amount."""

    grams = float(grams)

    if grams <= 0:
        raise ValueError("Grams must be a positive number.")

    serving_size = _number(nutrition.get("serving_size")) or 100.0
    serving_unit = str(nutrition.get("serving_unit") or "g").casefold()

    if serving_unit not in {"g", "gram", "grams"}:
        serving_size = 100.0

    multiplier = grams / serving_size

    return {
        "calories": _scale(nutrition.get("calories"), multiplier),
        "serving_size": f"{_format_number(grams)}g",
        "protein": _scale(nutrition.get("protein"), multiplier),
        "carbohydrates": _scale(nutrition.get("carbohydrates"), multiplier),
        "fat": _scale(nutrition.get("fat"), multiplier),
    }


def find_food_record(food_name: str) -> dict[str, Any] | None:
    """Find a canonical food record from the Food Knowledge Base."""

    normalized_food_name = normalize_name(food_name)

    if not normalized_food_name:
        return None

    for food in _knowledge_base_foods():
        names = [
            str(food.get("id", "")).replace("_", " "),
            food.get("display_name", ""),
        ]
        aliases = food.get("aliases", [])

        if isinstance(aliases, list):
            names.extend(alias for alias in aliases if isinstance(alias, str))

        if normalized_food_name in {normalize_name(name) for name in names}:
            return food

    return None


def _clean_name(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else UNKNOWN


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        if value.strip().casefold() in {"", "unknown", "n/a", "none", "null"}:
            return None

        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))

    return None


def _parse_serving(serving: Any) -> tuple[float | None, str | None]:
    serving_text = str(serving or "").strip()

    if not serving_text or serving_text.casefold() == "unknown":
        return None, None

    parenthesized = re.search(
        r"\((\d+(?:\.\d+)?)\s*(g|gram|grams|ml|milliliter|milliliters)\)",
        serving_text,
        flags=re.IGNORECASE,
    )
    if parenthesized:
        return float(parenthesized.group(1)), parenthesized.group(2).lower()

    leading = re.match(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?", serving_text)
    if leading:
        return float(leading.group(1)), (leading.group(2) or "g").lower()

    return None, None


def _food_nutrient(food: dict[str, Any], key: str) -> float | None:
    nutrient_ids, nutrient_names = NUTRIENTS[key]

    for nutrient in food.get("foodNutrients", []):
        if not isinstance(nutrient, dict):
            continue

        nutrient_id = _nutrient_id(nutrient)
        nutrient_name = normalize_name(nutrient.get("nutrientName", nutrient.get("name", "")))

        if nutrient_id not in nutrient_ids and nutrient_name not in nutrient_names:
            continue

        if key == "calories":
            unit = str(nutrient.get("unitName", "")).casefold()
            if unit and unit not in {"kcal", "calories"}:
                continue

        return _number(nutrient.get("value", nutrient.get("amount")))

    return None


def _nutrient_id(nutrient: dict[str, Any]) -> int | None:
    value = nutrient.get("nutrientId", nutrient.get("nutrient_id"))

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    return int(value) if isinstance(value, str) and value.isdigit() else None


def _usda_metadata(
    food: dict[str, Any],
    confidence: float | None = None,
) -> dict[str, Any] | None:
    fdc_id = food.get("fdcId", food.get("fdc_id"))
    description = food.get("description")

    if isinstance(fdc_id, bool) or fdc_id is None or not description:
        return None

    try:
        metadata = {
            "fdc_id": int(fdc_id),
            "description": str(description),
            "data_type": str(food.get("dataType", food.get("data_type", ""))),
        }

        if confidence is not None:
            metadata["confidence"] = round(float(confidence), 2)

        return metadata
    except (TypeError, ValueError):
        return None


def _knowledge_base_foods() -> list[dict[str, Any]]:
    try:
        with open(KNOWLEDGE_BASE_DIR / "manifest.json", "r", encoding="utf-8") as file:
            collections = json.load(file).get("collections", [])
    except (OSError, ValueError):
        return []

    foods: list[dict[str, Any]] = []

    for filename in collections:
        if not isinstance(filename, str):
            continue

        try:
            with open(KNOWLEDGE_BASE_DIR / filename, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, ValueError):
            continue

        if isinstance(payload, list):
            foods.extend(food for food in payload if isinstance(food, dict))
        elif isinstance(payload, dict) and isinstance(payload.get("foods"), list):
            foods.extend(food for food in payload["foods"] if isinstance(food, dict))

    return foods


def _resolve_food(food_name: str) -> tuple[str, str, list[str], Any]:
    record = find_food_record(food_name)

    if not record:
        return food_name.strip(), food_name.strip(), [], None

    display_name = record.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        display_name = food_name.strip()
    else:
        display_name = display_name.strip()
    aliases = record.get("aliases", [])
    usda = record.get("usda")
    query = display_name

    if isinstance(usda, dict) and isinstance(usda.get("description"), str):
        query = usda["description"].strip()
    elif isinstance(usda, str) and usda.strip():
        query = usda.strip()

    return display_name, query, aliases if isinstance(aliases, list) else [], usda


def _mapping_confidence(usda: Any) -> float | None:
    if not isinstance(usda, dict):
        return None

    confidence = usda.get("confidence")
    return float(confidence) if isinstance(confidence, (int, float)) else None


def _select_usda_food(foods: Any, usda: Any = None) -> dict[str, Any] | None:
    if not isinstance(foods, list):
        return None

    candidates = [food for food in foods if isinstance(food, dict)]

    for food in candidates:
        if _matches_usda_mapping(food, usda):
            return food

    for food in candidates:
        if isinstance(food.get("foodNutrients"), list):
            return food

    return candidates[0] if candidates else None


def _matches_usda_mapping(food: dict[str, Any], usda: Any) -> bool:
    if isinstance(usda, str):
        return normalize_name(usda) == normalize_name(food.get("description", ""))

    if not isinstance(usda, dict):
        return False

    fdc_id = usda.get("fdc_id")
    description = usda.get("description")

    if fdc_id is not None and str(food.get("fdcId", food.get("fdc_id"))) == str(fdc_id):
        return True

    return bool(description) and normalize_name(description) == normalize_name(food.get("description", ""))


def _has_macros(nutrition: dict[str, Any]) -> bool:
    return any(
        nutrition.get(key) is not None
        for key in ("calories", "protein", "fat", "carbohydrates")
    )


def _value_or_unknown(value: Any) -> float | str:
    number = _number(value)
    return number if number is not None else UNKNOWN


def _scale(value: Any, multiplier: float) -> float | str:
    number = _number(value)
    return round(number * multiplier, 2) if number is not None else UNKNOWN


def _format_serving(size: Any, unit: Any) -> str:
    size_text = _format_number(size)

    if size_text == UNKNOWN:
        return UNKNOWN

    return f"{size_text}{str(unit or 'g').strip()}"


def _format_number(value: Any) -> str:
    number = _number(value)

    if number is None:
        return UNKNOWN

    return str(int(number)) if number.is_integer() else str(round(number, 2)).rstrip("0").rstrip(".")
