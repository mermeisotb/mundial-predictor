import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

headers = {"x-apisports-key": API_FOOTBALL_KEY}
url = "https://v3.football.api-sports.io/leagues"
params = {"id": 1}

response = requests.get(url, headers=headers, params=params)
data = response.json()

print("Errors:", data.get("errors"))
print("Results:", data.get("results"))

for item in data.get("response", []):
    for season in item["seasons"]:
        print(f"Año: {season['year']} | Actual: {season.get('current')} | Coverage fixtures: {season['coverage']['fixtures']}")