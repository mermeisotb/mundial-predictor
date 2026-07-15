import os
import requests
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"


def get_world_cup_matches():
    """Trae los partidos del Mundial desde football-data.org"""
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    url = f"{FOOTBALL_DATA_BASE}/competitions/WC/matches"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    return response.json()


def get_fixture_statistics(fixture_id):
    """Trae estadísticas (córners, tarjetas, etc.) de un partido desde API-Football"""
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    url = f"{API_FOOTBALL_BASE}/fixtures/statistics"
    params = {"fixture": fixture_id}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    return response.json()


if __name__ == "__main__":
    print("Probando conexión con football-data.org...")
    data = get_world_cup_matches()

    if data:
        matches = data.get("matches", [])
        print(f"Se encontraron {len(matches)} partidos.")
        for match in matches[:5]:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            date = match["utcDate"]
            status = match["status"]
            print(f"{date} | {home} vs {away} | {status}")
    else:
        print("No se pudo traer la data. Revisá la key en .env")