import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
DB_PATH = "data/db.sqlite"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_world_cup_matches():
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    url = f"{FOOTBALL_DATA_BASE}/competitions/WC/matches"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return None

    return response.json()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            utc_date TEXT,
            stage TEXT,
            status TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER
        )
    """)
    conn.commit()
    return conn


def save_matches(matches):
    conn = init_db()
    cursor = conn.cursor()

    for m in matches:
        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]

        cursor.execute("""
            INSERT OR REPLACE INTO matches
            (id, utc_date, stage, status, home_team, away_team, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["id"], m["utcDate"], m["stage"], m["status"],
            m["homeTeam"]["name"], m["awayTeam"]["name"],
            home_score, away_score
        ))

    conn.commit()
    conn.close()
    print(f"{len(matches)} partidos guardados en {DB_PATH}")


if __name__ == "__main__":
    print("Trayendo partidos del Mundial...")
    data = get_world_cup_matches()

    if data:
        matches = data.get("matches", [])
        save_matches(matches)

        finished = [m for m in matches if m["status"] == "FINISHED"]
        upcoming = [m for m in matches if m["status"] in ("SCHEDULED", "TIMED")]
        print(f"Finalizados: {len(finished)} | Próximos: {len(upcoming)}")
    else:
        print("No se pudo traer la data. Revisá la key en .env")