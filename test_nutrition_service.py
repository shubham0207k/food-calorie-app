from types import SimpleNamespace
import unittest

from app.services.nutrition_service import (
    SOURCE_LOCAL,
    calculate_nutrition_for_grams,
    get_nutrition,
    normalize_nutrition_response,
    nutrition_from_usda_food,
    to_legacy_nutrition,
)


USDA_APPLE = {
    "fdcId": 123,
    "description": "Apple, raw",
    "dataType": "Foundation",
    "foodNutrients": [
        {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 52},
        {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 0.26},
        {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 13.8},
        {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.17},
    ],
}


class NutritionServiceTests(unittest.TestCase):
    def test_normalizes_legacy_nutrition_and_parses_serving_grams(self):
        nutrition = normalize_nutrition_response(
            "apple",
            {
                "calories": 95,
                "serving": "1 medium (182g)",
                "protein": "0.5g",
                "carbs": "25g",
                "fat": "0.3g",
            },
            source=SOURCE_LOCAL,
        )

        self.assertTrue(nutrition["nutrition_available"])
        self.assertEqual(nutrition["calories"], 95.0)
        self.assertEqual(nutrition["protein"], 0.5)
        self.assertEqual(nutrition["carbohydrates"], 25.0)
        self.assertEqual(nutrition["serving_size"], 182.0)
        self.assertEqual(nutrition["serving_unit"], "g")
        self.assertEqual(nutrition["source"], SOURCE_LOCAL)

    def test_extracts_nutrients_from_usda_search_result(self):
        nutrition = nutrition_from_usda_food(
            USDA_APPLE,
            food_name="Apple",
            confidence=0.86,
        )

        self.assertTrue(nutrition["nutrition_available"])
        self.assertEqual(nutrition["calories"], 52.0)
        self.assertEqual(nutrition["protein"], 0.26)
        self.assertEqual(nutrition["carbohydrates"], 13.8)
        self.assertEqual(nutrition["fat"], 0.17)
        self.assertEqual(nutrition["serving_size"], 100.0)
        self.assertEqual(nutrition["serving_unit"], "g")
        self.assertEqual(nutrition["usda"]["fdc_id"], 123)
        self.assertEqual(nutrition["usda"]["confidence"], 0.86)

    def test_get_nutrition_uses_knowledge_base_usda_mapping_before_matching(self):
        queries = []

        def fake_search(query):
            queries.append(query)
            return {"foods": [USDA_APPLE]}

        def fail_matcher(*args, **kwargs):
            raise AssertionError("matcher should not run when KB has a USDA mapping")

        nutrition = get_nutrition(
            "apple",
            search_func=fake_search,
            matcher_func=fail_matcher,
        )

        self.assertEqual(queries, ["Apple, raw"])
        self.assertEqual(nutrition["food_name"], "Apple")
        self.assertEqual(nutrition["calories"], 52.0)

    def test_get_nutrition_uses_matcher_for_unmapped_foods(self):
        queries = []

        def fake_search(query):
            queries.append(query)
            return {"foods": [USDA_APPLE]}

        def fake_matcher(food):
            self.assertEqual(food["display_name"], "Imaginary Food")
            return SimpleNamespace(
                status="matched",
                usda={
                    "fdc_id": 123,
                    "description": "Apple, raw",
                    "data_type": "Foundation",
                    "confidence": 0.75,
                },
                confidence=0.75,
                query="apple",
                warning=None,
            )

        nutrition = get_nutrition(
            "Imaginary Food",
            search_func=fake_search,
            matcher_func=fake_matcher,
        )

        self.assertEqual(queries, ["Apple, raw"])
        self.assertEqual(nutrition["confidence"], 0.75)
        self.assertEqual(nutrition["calories"], 52.0)

    def test_legacy_conversion_and_gram_scaling_preserve_api_shape(self):
        nutrition = nutrition_from_usda_food(USDA_APPLE, food_name="Apple")

        self.assertEqual(
            to_legacy_nutrition(nutrition),
            {
                "calories": 52.0,
                "serving": "100g",
                "protein": 0.26,
                "carbs": 13.8,
                "fat": 0.17,
            },
        )

        self.assertEqual(
            calculate_nutrition_for_grams(nutrition, 50),
            {
                "calories": 26.0,
                "serving_size": "50g",
                "protein": 0.13,
                "carbohydrates": 6.9,
                "fat": 0.09,
            },
        )


if __name__ == "__main__":
    unittest.main()
