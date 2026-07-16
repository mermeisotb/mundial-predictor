import requests
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://worldcup26.ir"
DB_PATH = "data/db.sqlite"


def register_or_login():
    """Registra el usuario (una sola vez) o loguea si ya existe. Devuelve el token JWT."""
    email = os.getenv("WC26_EMAIL")
    password = os.getenv("WC26_PASSWORD")

    resp = requests.post(f"{BASE_URL}/auth/authenticate", json={
        "email": email,
        "password": password
    })
    if resp.status_code == 200:
        return resp.json()["token"]

    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "name": "mundial-predictor",
        "email": email,
        "password": password
    })
    if resp.status_code == 200:
        return resp.json()["token"]

    print(f"Error: {resp.status_code} - {resp.text}")
    return None


def get_matches(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/get/games", headers=headers)
    if resp.status_code == 200:
        return resp.json().get("games", [])
    print(f"Error trayendo partidos: {resp.status_code} - {resp.text}")
    return []


def save_matches(matches):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS worldcup26_matches (
            id TEXT PRIMARY KEY,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            group_name TEXT,
            matchday TEXT,
            local_date TEXT,
            stadium_id TEXT,
            finished TEXT,
            stage TEXT
        )
    """)
    for m in matches:
        cursor.execute("""
            INSERT OR REPLACE INTO worldcup26_matches
            (id, home_team, away_team, home_score, away_score, group_name, matchday, local_date, stadium_id, finished, stage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m.get("id"),
            m.get("home_team_name_en"),
            m.get("away_team_name_en"),
            m.get("home_score"),
            m.get("away_score"),
            m.get("group"),
            m.get("matchday"),
            m.get("local_date"),
            m.get("stadium_id"),
            m.get("finished"),
            m.get("type"),
        ))
    conn.commit()
    conn.close()
    print(f"{len(matches)} partidos guardados en la base de datos.")


if __name__ == "__main__":
    token = register_or_login()
    if token:
        print("Token obtenido correctamente.")
        matches = get_matches(token)
        print(f"Se encontraron {len(matches)} partidos.")
        save_matches(matches)
    else:
        print("No se pudo obtener el token.")