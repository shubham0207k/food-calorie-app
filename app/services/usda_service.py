"""Backward-compatible USDA nutrition adapter."""

from __future__ import annotations

from app.services.nutrition_service import get_nutrition, to_legacy_nutrition


def get_calories_from_api(food_name):
    """Return the legacy calorie dictionary expected by existing routes."""

    nutrition = get_nutrition(food_name)

    if not nutrition.get("nutrition_available"):
        return None

    return to_legacy_nutrition(nutrition)
