import requests
import json
import base64

key = "cbc0a49a13d34afc8b640ad1f63e48c7"
# Use a sample image of a pizza or similar. Or we can pass base64 bytes of a mock/dummy image.
# Let's create a dummy 1x1 image base64
dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

url = "https://api.clarifai.com/v2/users/clarifai/apps/main/models/food-item-recognition/outputs"
headers = {
    "Authorization": f"Key {key}",
    "Content-Type": "application/json"
}
body = {
    "inputs": [
        {
            "data": {
                "image": {
                    "base64": dummy_image_b64
                }
            }
        }
    ]
}

response = requests.post(url, headers=headers, json=body)
print("STATUS:", response.status_code)
try:
    print("RESPONSE:", json.dumps(response.json(), indent=2))
except Exception as e:
    print("ERROR parsing JSON:", e)
