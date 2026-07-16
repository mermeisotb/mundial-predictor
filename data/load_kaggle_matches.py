"""
Carga matches.csv, match_team_stats.csv y match_prediction_features.csv
(dataset Kaggle: FIFA World Cup 2026 - Live & Updated Stats) a data/db.sqlite.
Solo carga los datos crudos a SQLite; no modifica los modelos existentes.

Requiere los 3 CSV en data/kaggle/.

Uso: python data/load_kaggle_matches.py
"""

import csv
import sqlite3

DB_PATH = "data/db.sqlite"
MATCHES_CSV = "data/kaggle/matches.csv"
TEAM_STATS_CSV = "data/kaggle/match_team_stats.csv"
FEATURES_CSV = "data/kaggle/match_prediction_features.csv"

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


def to_float(v):
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def to_int(v):
    try:
        return int(float(v)) if v not in (None, "") else None
    except ValueError:
        return None


def load_matches(conn):
    rows = read_csv(MATCHES_CSV)
    conn.execute("DROP TABLE IF EXISTS kaggle_matches")
    conn.execute("""
        CREATE TABLE kaggle_matches (
            match_id INTEGER PRIMARY KEY,
            date TEXT,
            kickoff_time_utc TEXT,
            stage_id INTEGER,
            venue_id INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_team_name TEXT,
            away_team_name TEXT,
            home_score INTEGER,
            away_score INTEGER,
            home_penalty_score INTEGER,
            away_penalty_score INTEGER,
            status TEXT,
            result_type TEXT,
            home_xg REAL,
            away_xg REAL,
            referee_id INTEGER,
            player_of_the_match_id INTEGER
        )
    """)
    data = []
    for r in rows:
        data.append((
            to_int(r["match_id"]), r["date"], r["kickoff_time_utc"],
            to_int(r["stage_id"]), to_int(r["venue_id"]),
            to_int(r["home_team_id"]), to_int(r["away_team_id"]),
            TEAM_NAMES.get(r["home_team_id"], "Desconocido"),
            TEAM_NAMES.get(r["away_team_id"], "Desconocido"),
            to_int(r["home_score"]), to_int(r["away_score"]),
            to_int(r["home_penalty_score"]), to_int(r["away_penalty_score"]),
            r["status"], r["result_type"],
            to_float(r["home_xg"]), to_float(r["away_xg"]),
            to_int(r["referee_id"]), to_int(r["player_of_the_match_id"]),
        ))
    conn.executemany("""
        INSERT INTO kaggle_matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, data)
    print(f"[OK] kaggle_matches: {len(data)} filas")


def load_team_stats(conn):
    rows = read_csv(TEAM_STATS_CSV)
    conn.execute("DROP TABLE IF EXISTS kaggle_match_team_stats")
    conn.execute("""
        CREATE TABLE kaggle_match_team_stats (
            match_id INTEGER,
            team_id INTEGER,
            team_name TEXT,
            possession_pct REAL,
            total_shots INTEGER,
            shots_on_target INTEGER,
            corners INTEGER,
            fouls INTEGER,
            offsides INTEGER,
            saves INTEGER,
            player_of_the_match TEXT,
            data_source TEXT,
            last_updated TEXT
        )
    """)
    data = []
    for r in rows:
        data.append((
            to_int(r["match_id"]), to_int(r["team_id"]),
            TEAM_NAMES.get(r["team_id"], "Desconocido"),
            to_float(r["possession_pct"]), to_int(r["total_shots"]),
            to_int(r["shots_on_target"]), to_int(r["corners"]),
            to_int(r["fouls"]), to_int(r["offsides"]), to_int(r["saves"]),
            r["player_of_the_match"], r["data_source"], r["last_updated"],
        ))
    conn.executemany("""
        INSERT INTO kaggle_match_team_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, data)
    print(f"[OK] kaggle_match_team_stats: {len(data)} filas")


def load_prediction_features(conn):
    rows = read_csv(FEATURES_CSV)
    if not rows:
        print("[!] match_prediction_features.csv vacío, se omite.")
        return
    columns = list(rows[0].keys())
    conn.execute("DROP TABLE IF EXISTS kaggle_match_prediction_features")
    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    conn.execute(f"CREATE TABLE kaggle_match_prediction_features ({col_defs})")
    placeholders = ", ".join("?" for _ in columns)
    data = [tuple(r[c] for c in columns) for r in rows]
    conn.executemany(
        f"INSERT INTO kaggle_match_prediction_features VALUES ({placeholders})",
        data,
    )
    print(f"[OK] kaggle_match_prediction_features: {len(data)} filas")


def main():
    conn = sqlite3.connect(DB_PATH)
    load_matches(conn)
    load_team_stats(conn)
    load_prediction_features(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()