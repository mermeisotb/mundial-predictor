import os
import sqlite3

import requests
from dotenv import load_dotenv

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
DB_PATH = "data/db.sqlite"
SPORT = "soccer_fifa_world_cup"
REGIONS = "eu"
MARKETS = "h2h"


def init_odds_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    columns = cursor.execute("PRAGMA table_info(match_odds)").fetchall()

    # The Odds API uses string IDs, while an earlier version of this script
    # created this column as INTEGER PRIMARY KEY. Rebuild it once if needed.
    if columns and columns[0][2].upper() != "TEXT":
        cursor.execute("ALTER TABLE match_odds RENAME TO match_odds_old")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_odds (
            match_id TEXT PRIMARY KEY,
            bookmaker TEXT,
            home_team TEXT,
            away_team TEXT,
            odd_home REAL,
            odd_draw REAL,
            odd_away REAL,
            last_update TEXT,
            commence_time TEXT
        )
    """)

    existing_columns = {column[1] for column in cursor.execute("PRAGMA table_info(match_odds)")}
    for column in ("home_team", "away_team", "commence_time"):
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE match_odds ADD COLUMN {column} TEXT")

    if columns and columns[0][2].upper() != "TEXT":
        cursor.execute("""
            INSERT INTO match_odds
            (match_id, bookmaker, odd_home, odd_draw, odd_away, last_update)
            SELECT CAST(match_id AS TEXT), bookmaker, odd_home, odd_draw, odd_away, last_update
            FROM match_odds_old
        """)
        cursor.execute("DROP TABLE match_odds_old")

    conn.commit()
    conn.close()


def save_odds(match_id, bookmaker, home_team, away_team, home, draw, away, updated, commence_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO match_odds
        (match_id, bookmaker, home_team, away_team, odd_home, odd_draw, odd_away, last_update, commence_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (match_id, bookmaker, home_team, away_team, home, draw, away, updated, commence_time))
    conn.commit()
    conn.close()


def main():
    if not ODDS_API_KEY:
        raise RuntimeError("Falta definir ODDS_API_KEY en el archivo .env")

    init_odds_table()
    url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
        f"?apiKey={ODDS_API_KEY}&regions={REGIONS}&markets={MARKETS}"
    )
    response = requests.get(url, timeout=30)
    print("Status:", response.status_code)
    response.raise_for_status()

    matches = response.json()
    print(f"Partidos encontrados: {len(matches)}")

    for match in matches:
        bookmakers = match.get("bookmakers", [])
        if not bookmakers:
            print(f'Sin cuotas disponibles para {match["home_team"]} vs {match["away_team"]}')
            continue

        bookmaker = bookmakers[0]
        market = next(
            (m for m in bookmaker.get("markets", []) if m["key"] == "h2h"),
            None,
        )
        if market is None:
            print(f'Sin mercado h2h para {match["home_team"]} vs {match["away_team"]}')
            continue

        odds = {}
        for outcome in market["outcomes"]:
            if outcome["name"] == match["home_team"]:
                odds["home"] = outcome["price"]
            elif outcome["name"] == match["away_team"]:
                odds["away"] = outcome["price"]
            else:
                odds["draw"] = outcome["price"]

        if not {"home", "draw", "away"}.issubset(odds):
            print(f'Cuotas incompletas para {match["home_team"]} vs {match["away_team"]}')
            continue

        save_odds(
            match["id"],
            bookmaker["title"],
            match["home_team"],
            match["away_team"],
            odds["home"],
            odds["draw"],
            odds["away"],
            bookmaker.get("last_update", match["commence_time"]),
            match["commence_time"],
        )
        print(f'✓ {match["home_team"]} vs {match["away_team"]} guardado')


if __name__ == "__main__":
    main()
