import os
import sqlite3
import requests
from scipy.stats import poisson
from dotenv import load_dotenv

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
HEADERS = {"x-apisports-key": API_FOOTBALL_KEY}
BASE_URL = "https://v3.football.api-sports.io"
DB_PATH = "data/db.sqlite"
REFERENCE_SEASON = 2022


def init_stats_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fixture_stats (
            fixture_id INTEGER,
            team_name TEXT,
            corners INTEGER,
            yellow INTEGER,
            red INTEGER,
            PRIMARY KEY (fixture_id, team_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_fixtures (
            fixture_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    return conn


def get_2022_fixtures():
    url = f"{BASE_URL}/fixtures"
    params = {"league": 1, "season": REFERENCE_SEASON}
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()
    if data.get("errors"):
        print("Error:", data["errors"])
        return []
    return data.get("response", [])


def get_fixture_stats(fixture_id):
    url = f"{BASE_URL}/fixtures/statistics"
    response = requests.get(url, headers=HEADERS, params={"fixture": fixture_id})
    data = response.json()
    if data.get("errors"):
        return None  # distinto de [] vacío legítimo, esto marca error real (ej. cuota agotada)
    return data.get("response", [])


def already_processed(conn, fixture_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM processed_fixtures WHERE fixture_id = ?", (fixture_id,))
    return cursor.fetchone() is not None


def save_fixture_stats(conn, fixture_id, stats):
    cursor = conn.cursor()
    for team_stats in stats:
        team_name = team_stats["team"]["name"]
        corners = yellow = red = 0
        for stat in team_stats["statistics"]:
            value = stat["value"] if stat["value"] is not None else 0
            if stat["type"] == "Corner Kicks":
                corners = value
            elif stat["type"] == "Yellow Cards":
                yellow = value
            elif stat["type"] == "Red Cards":
                red = value
        cursor.execute("""
            INSERT OR REPLACE INTO fixture_stats (fixture_id, team_name, corners, yellow, red)
            VALUES (?, ?, ?, ?, ?)
        """, (fixture_id, team_name, corners, yellow, red))

    cursor.execute("INSERT OR IGNORE INTO processed_fixtures (fixture_id) VALUES (?)", (fixture_id,))
    conn.commit()


def build_dataset(max_requests=90):
    """Recorre fixtures pendientes, se detiene solo si se acerca al límite diario"""
    conn = init_stats_table()
    fixtures = get_2022_fixtures()
    requests_used = 1  # ya gastamos 1 en get_2022_fixtures

    pending = [f for f in fixtures if not already_processed(conn, f["fixture"]["id"])]
    print(f"Fixtures totales: {len(fixtures)} | Ya procesados: {len(fixtures) - len(pending)} | Pendientes: {len(pending)}")

    for f in pending:
        if requests_used >= max_requests:
            print(f"Frenando en {requests_used} requests para no agotar la cuota diaria. Correr de nuevo mañana.")
            break

        fixture_id = f["fixture"]["id"]
        stats = get_fixture_stats(fixture_id)
        requests_used += 1

        if stats is None:
            print("Cuota probablemente agotada, frenando acá.")
            break

        if stats:
            save_fixture_stats(conn, fixture_id, stats)

    conn.close()
    print(f"Requests usados esta corrida: {requests_used}")


def get_team_averages():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_name, AVG(corners), AVG(yellow), AVG(red), COUNT(*)
        FROM fixture_stats
        GROUP BY team_name
    """)
    rows = cursor.fetchall()
    conn.close()

    averages = {}
    for team, avg_corners, avg_yellow, avg_red, n in rows:
        averages[team] = {
            "avg_corners": avg_corners,
            "avg_yellow": avg_yellow,
            "avg_red": avg_red,
            "sample_size": n,
        }
    return averages


def predict_corners_cards(home_team, away_team, averages):
    home = averages.get(home_team, {"avg_corners": 5.0, "avg_yellow": 2.0, "avg_red": 0.05})
    away = averages.get(away_team, {"avg_corners": 5.0, "avg_yellow": 2.0, "avg_red": 0.05})

    lambda_corners = home["avg_corners"] + away["avg_corners"]
    lambda_cards = home["avg_yellow"] + away["avg_yellow"]

    return {
        "expected_corners": round(lambda_corners, 1),
        "expected_cards": round(lambda_cards, 1),
        "over_9_5_corners_prob": round((1 - poisson.cdf(9, lambda_corners)) * 100, 1),
        "over_3_5_cards_prob": round((1 - poisson.cdf(3, lambda_cards)) * 100, 1),
        "note": "Estimación basada en Mundial 2022 (API-Football free no cubre 2026 en vivo)",
    }


if __name__ == "__main__":
    build_dataset()
    averages = get_team_averages()
    print(f"\nSelecciones con datos: {len(averages)}")