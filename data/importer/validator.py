REQUIRED_FIELDS = [
    "id",
    "display_name",
    "category",
    "type",
]


def validate_usda_field(value):
    """
    Validate the optional USDA link field.
    """

    if value is None:
        return []

    if isinstance(value, str):
        return []

    if not isinstance(value, dict):
        return ["usda must be a string, object, or null"]

    errors = []
    fdc_id = value.get("fdc_id")
    description = value.get("description")
    data_type = value.get("data_type")
    confidence = value.get("confidence")

    if isinstance(fdc_id, bool) or not isinstance(fdc_id, int):
        errors.append("usda.fdc_id must be an integer")

    if not isinstance(description, str) or not description.strip():
        errors.append("usda.description must be a non-empty string")

    if not isinstance(data_type, str):
        errors.append("usda.data_type must be a string")

    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 1
    ):
        errors.append("usda.confidence must be between 0.00 and 1.00")

    return errors


def validate_food(food):
    """
    Validate a FoodVision AI food record.
    """

    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        value = food.get(field)

        if value is None:
            errors.append(f"Missing required field: {field}")
        elif isinstance(value, str) and not value.strip():
            errors.append(f"Empty required field: {field}")

    # Validate field types
    if "aliases" in food and not isinstance(food["aliases"], list):
        errors.append("aliases must be a list")

    if "usda" in food:
        errors.extend(validate_usda_field(food["usda"]))

    if "recognizable" in food and not isinstance(food["recognizable"], bool):
        errors.append("recognizable must be a boolean")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
