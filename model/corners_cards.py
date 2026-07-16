import os
import sqlite3
import requests
import sqlite3
from collections import defaultdict
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
    # Creamos un diccionario con valores por defecto por si la tabla no existe
    # Evita que el resto del código lance un KeyError
    default_stats = {
        "corners": 4.5,
        "yellow": 2.0,
        "red": 0.1,
        "matches": 5
    }
    averages = defaultdict(lambda: default_stats)

    try:
        conn = sqlite3.connect("data/db.sqlite")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_name, AVG(corners), AVG(yellow), AVG(red), COUNT(*)
            FROM fixture_stats
            GROUP BY team_name
        """)
        rows = cursor.fetchall()
        conn.close()
        
        # Si la tabla existe y tiene datos, llenamos el diccionario con los valores reales
        for row in rows:
            averages[row[0]] = {
                "corners": row[1] if row[1] is not None else 4.5,
                "yellow": row[2] if row[2] is not None else 2.0,
                "red": row[3] if row[3] is not None else 0.1,
                "matches": row[4]
            }
        return averages

    except sqlite3.OperationalError:
        # 🛡️ Si la tabla 'fixture_stats' no existe en la BD limpia, evitamos el crash
        # y devolvemos el diccionario con las estadísticas por defecto
        return averages


def predict_corners_cards(home_team, away_team, averages):
    # Keep these names aligned with get_team_averages(). Using different
    # names here previously raised a KeyError for every team with real data.
    default_stats = {"corners": 4.5, "yellow": 2.0, "red": 0.1}
    home = averages.get(home_team, default_stats)
    away = averages.get(away_team, default_stats)

    lambda_corners = home.get("corners", 4.5) + away.get("corners", 4.5)
    lambda_cards = home.get("yellow", 2.0) + away.get("yellow", 2.0)

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
