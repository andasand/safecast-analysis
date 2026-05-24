import requests

BASE_URL = "https://api.safecast.org/en-US"

def get(path, params=None):
    url = f"{BASE_URL}{path}"
    response = requests.get(url, params=params, timeout=30)
    print("URL:", response.url)
    print("Status:", response.status_code)
    response.raise_for_status()
    return response.json()

print("\n--- Latest bGeigie imports ---")
imports = get("/bgeigie_imports.json")
print(imports[:3])

print("\n--- Measurements near Thummalapalle area ---")
measurements = get(
    "/measurements.json",
    params={
        "latitude": 14.42,
        "longitude": 78.23,
        "distance": 10000,
    },
)
print(measurements[:5])
