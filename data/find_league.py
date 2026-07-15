import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

headers = {"x-apisports-key": API_FOOTBALL_KEY}
url = "https://v3.football.api-sports.io/leagues"
params = {"search": "World Cup"}

response = requests.get(url, headers=headers, params=params)
data = response.json()

for item in data.get("response", []):
    league = item["league"]
    country = item["country"]["name"]
    seasons = [s["year"] for s in item["seasons"] if s.get("year") == 2026]
    if seasons or "world" in league["name"].lower():
        print(f"ID: {league['id']} | Nombre: {league['name']} | País: {country}")