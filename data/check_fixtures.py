import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

headers = {"x-apisports-key": API_FOOTBALL_KEY}
url = "https://v3.football.api-sports.io/fixtures"
params = {"league": 1, "season": 2026}

response = requests.get(url, headers=headers, params=params)
data = response.json()
print("Errors:", data.get("errors"))
print("Results:", data.get("results"))

fixtures = data.get("response", [])
print(f"Total fixtures encontrados: {len(fixtures)}")

for f in fixtures[:5]:
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    date = f["fixture"]["date"]
    fixture_id = f["fixture"]["id"]
    status = f["fixture"]["status"]["short"]
    print(f"ID: {fixture_id} | {date} | {home} vs {away} | {status}")