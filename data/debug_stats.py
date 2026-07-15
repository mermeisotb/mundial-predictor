import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
headers = {"x-apisports-key": API_FOOTBALL_KEY}

# traigo un fixture cualquiera del Mundial 2022 para inspeccionar
url = "https://v3.football.api-sports.io/fixtures"
params = {"league": 1, "season": 2022, "team": 26}  # 26 suele ser Argentina en API-Football, si no jala probamos otro
response = requests.get(url, headers=headers, params=params)
fixtures = response.json().get("response", [])

if not fixtures:
    print("No se encontró team=26, probemos sin filtro de team")
else:
    fixture_id = fixtures[0]["fixture"]["id"]
    print(f"Usando fixture ID: {fixture_id}")

    stats_url = "https://v3.football.api-sports.io/fixtures/statistics"
    stats_response = requests.get(stats_url, headers=headers, params={"fixture": fixture_id})
    stats_data = stats_response.json().get("response", [])

    for team_stats in stats_data:
        print(f"\nEquipo: {team_stats['team']['name']}")
        for stat in team_stats["statistics"]:
            print(f"  {stat['type']}: {stat['value']}")