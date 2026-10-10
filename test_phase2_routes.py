import io
import unittest

import main


class Phase2RouteTests(unittest.TestCase):
    def setUp(self):
        self.original_predict_food = main.predict_food
        self.original_get_nutrition = main.get_nutrition
        self.original_load_json_db = main.load_json_db
        self.original_save_json_db = main.save_json_db
        self.original_sleep = main.time.sleep
        main.time.sleep = lambda _seconds: None
        self.client = main.app.test_client()

    def tearDown(self):
        main.predict_food = self.original_predict_food
        main.get_nutrition = self.original_get_nutrition
        main.load_json_db = self.original_load_json_db
        main.save_json_db = self.original_save_json_db
        main.time.sleep = self.original_sleep

    def test_predict_uses_nutrition_service_and_preserves_response_shape(self):
        def fake_predict_food(_image_data):
            return "Pizza", 0.93, [{"name": "Pizza", "confidence": 93}]

        def fake_get_nutrition(food_name):
            self.assertEqual(food_name, "pizza")
            return {
                "food_name": "Pizza",
                "nutrition_available": True,
                "calories": 266.0,
                "protein": 11.4,
                "carbohydrates": 33.3,
                "fat": 9.7,
                "serving_size": 100.0,
                "serving_unit": "g",
                "source": "USDA FoodData Central",
                "confidence": 0.82,
                "usda": {
                    "fdc_id": 123,
                    "description": "Pizza, cheese",
                    "data_type": "Survey (FNDDS)",
                    "confidence": 0.82,
                },
            }

        main.predict_food = fake_predict_food
        main.get_nutrition = fake_get_nutrition

        response = self.client.post(
            "/predict",
            data={"image": (io.BytesIO(b"fake image bytes"), "pizza.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["final_food"], "Pizza")
        self.assertEqual(payload["calories_data"]["calories"], 266.0)
        self.assertEqual(payload["calories_data"]["serving_size"], "100g")
        self.assertEqual(payload["prediction"]["nutrition"]["carbohydrates"], 33.3)

    def test_predict_unknown_food_skips_nutrition_lookup(self):
        def fake_predict_food(_image_data):
            return "Unknown Food", 0.02, []

        def fail_get_nutrition(_food_name):
            raise AssertionError("nutrition lookup should not run for unknown foods")

        main.predict_food = fake_predict_food
        main.get_nutrition = fail_get_nutrition

        response = self.client.post(
            "/predict",
            data={"image": (io.BytesIO(b"fake image bytes"), "unknown.jpg")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["is_unknown"])
        self.assertEqual(payload["calories_data"]["calories"], "Unknown")

    def test_manual_grams_uses_nutrition_service_calculation(self):
        def fake_get_nutrition(food_name):
            self.assertEqual(food_name, "apple")
            return {
                "food_name": "Apple",
                "nutrition_available": True,
                "calories": 52.0,
                "protein": 0.26,
                "carbohydrates": 13.8,
                "fat": 0.17,
                "serving_size": 100.0,
                "serving_unit": "g",
                "source": "USDA FoodData Central",
                "confidence": 0.9,
                "usda": None,
            }

        main.get_nutrition = fake_get_nutrition

        response = self.client.post(
            "/manual",
            json={"food": "apple", "grams": 50},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["nutrition"]["calories"], 26.0)
        self.assertEqual(payload["nutrition"]["protein"], 0.13)
        self.assertEqual(payload["nutrition"]["serving_size"], "50g")

    def test_manual_direct_calculation_accepts_existing_frontend_units(self):
        response = self.client.post(
            "/manual",
            json={
                "food": "rice",
                "calories_per_unit": 200,
                "unit": "servings",
                "quantity": 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["nutrition"]["unit"], "servings")
        self.assertEqual(payload["nutrition"]["total_calories"], 400.0)

    def test_activity_history_route_preserves_log_shape(self):
        saved = {}

        def fake_load_json_db(path):
            path_text = str(path)

            if path_text.endswith("users.json"):
                return [
                    {
                        "id": 1,
                        "username": "student",
                        "email": "student@example.com",
                    }
                ]

            if path_text.endswith("activity_logs.json"):
                return []

            return []

        def fake_save_json_db(path, data):
            saved[str(path)] = data

        main.load_json_db = fake_load_json_db
        main.save_json_db = fake_save_json_db

        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["username"] = "student"
            session["email"] = "student@example.com"

        response = self.client.post(
            "/api/log_activity",
            json={
                "action_type": "search",
                "food_name": "Apple",
                "quantity": "50g",
                "calories": 26,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        saved_logs = next(
            data
            for path, data in saved.items()
            if path.endswith("activity_logs.json")
        )
        self.assertEqual(saved_logs[0]["food_name"], "Apple")
        self.assertEqual(saved_logs[0]["quantity"], "50g")
        self.assertEqual(saved_logs[0]["calories"], 26)

    def test_dashboard_and_foods_api_still_respond(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertIn("apple", self.client.get("/api/foods").get_json()["foods"])

        dashboard_response = self.client.get("/user-dashboard")
        self.assertEqual(dashboard_response.status_code, 302)
        self.assertIn("/login", dashboard_response.location)


if __name__ == "__main__":
    unittest.main()
