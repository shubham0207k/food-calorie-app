import requests

key = "cbc0a49a13d34afc8b640ad1f63e48c7"

def check(name, url, headers):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        print(f"{name}: {res.status_code}")
        if res.status_code == 200:
            print(f"✅ It is a {name} API key!")
    except Exception as e:
        print(f"{name} Error:", e)

check("Clarifai", "https://api.clarifai.com/v2/users/me", {"Authorization": f"Key {key}"})
check("LogMeals", "https://api.logmeals.com/v2/users/me", {"Authorization": f"Bearer {key}"})
check("HuggingFace", "https://huggingface.co/api/whoami-v2", {"Authorization": f"Bearer {key}"})
