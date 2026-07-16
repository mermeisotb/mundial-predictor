"""
Carga los datasets de jugadores del Mundial 2026 (Kaggle: FIFA World Cup 2026
Dataset - Live & Updated Stats) a data/db.sqlite, tabla `players`.

Requiere: squads_and_players.csv y player_stats.csv en la carpeta data/kaggle/
(o ajusta las rutas abajo).

Uso: python data/load_players.py
"""

import csv
import sqlite3

DB_PATH = "data/db.sqlite"
SQUADS_CSV = "data/kaggle/squads_and_players.csv"
STATS_CSV = "data/kaggle/player_stats.csv"

# Mapeo team_id -> nombre de selección, extraído de match_prediction_features.csv
TEAM_NAMES = {
    "1": "Mexico", "2": "South Africa", "3": "South Korea", "4": "Czechia",
    "5": "Canada", "6": "Bosnia and Herzegovina", "7": "Qatar", "8": "Switzerland",
    "9": "Brazil", "10": "Morocco", "11": "Haiti", "12": "Scotland",
    "13": "United States", "14": "Paraguay", "15": "Australia", "16": "Türkiye",
    "17": "Germany", "18": "Curaçao", "19": "Côte d'Ivoire", "20": "Ecuador",
    "21": "Netherlands", "22": "Japan", "23": "Sweden", "24": "Tunisia",
    "25": "Belgium", "26": "Egypt", "27": "IR Iran", "28": "New Zealand",
    "29": "Spain", "30": "Cabo Verde", "31": "Saudi Arabia", "32": "Uruguay",
    "33": "France", "34": "Senegal", "35": "Iraq", "36": "Norway",
    "37": "Argentina", "38": "Algeria", "39": "Austria", "40": "Jordan",
    "41": "Portugal", "42": "Congo DR", "43": "Uzbekistan", "44": "Colombia",
    "45": "England", "46": "Croatia", "47": "Ghana", "48": "Panama",
}


def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def to_int(value):
    try:
        return int(float(value)) if value not in (None, "") else None
    except ValueError:
        return None


def setup_table(conn):
    conn.execute("DROP TABLE IF EXISTS players")
    conn.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            player_name TEXT,
            team_id INTEGER,
            team_name TEXT,
            position TEXT,
            club_team TEXT,
            market_value_eur INTEGER,
            caps INTEGER,
            date_of_birth TEXT,
            height_cm INTEGER,
            matches_played INTEGER,
            matches_started INTEGER,
            minutes_played INTEGER,
            goals INTEGER,
            assists INTEGER,
            shots INTEGER,
            shots_on_target INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER,
            average_rating REAL,
            clean_sheets INTEGER,
            saves INTEGER,
            goals_conceded INTEGER
        )
    """)


def main():
    squads = {row["player_id"]: row for row in read_csv(SQUADS_CSV)}
    stats = {row["player_id"]: row for row in read_csv(STATS_CSV)}

    conn = sqlite3.connect(DB_PATH)
    setup_table(conn)

    rows = []
    all_ids = set(squads) | set(stats)
    for pid in all_ids:
        sq = squads.get(pid, {})
        st = stats.get(pid, {})
        team_id = sq.get("team_id") or st.get("team_id")
        rows.append((
            to_int(pid),
            sq.get("player_name") or st.get("player_name"),
            to_int(team_id),
            TEAM_NAMES.get(team_id, "Desconocido"),
            sq.get("position") or st.get("position"),
            sq.get("club_team"),
            to_int(sq.get("market_value_eur")),
            to_int(sq.get("caps")),
            sq.get("date_of_birth"),
            to_int(sq.get("height_cm")),
            to_int(st.get("matches_played")),
            to_int(st.get("matches_started")),
            to_int(st.get("minutes_played")),
            to_int(st.get("goals")),
            to_int(st.get("assists")),
            to_int(st.get("shots")),
            to_int(st.get("shots_on_target")),
            to_int(st.get("yellow_cards")),
            to_int(st.get("red_cards")),
            to_float(st.get("average_rating")),
            to_int(st.get("clean_sheets")),
            to_int(st.get("saves")),
            to_int(st.get("goals_conceded")),
        ))

    conn.executemany("""
        INSERT INTO players (
            player_id, player_name, team_id, team_name, position, club_team,
            market_value_eur, caps, date_of_birth, height_cm,
            matches_played, matches_started, minutes_played, goals, assists,
            shots, shots_on_target, yellow_cards, red_cards, average_rating,
            clean_sheets, saves, goals_conceded
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    print(f"[OK] {len(rows)} jugadores cargados en la tabla players.")


if __name__ == "__main__":
    main()