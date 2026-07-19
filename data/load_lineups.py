# data/load_lineups.py

import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = "data/db.sqlite"
LINEUPS_DIR = "data/lineups"


def create_lineups_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            team TEXT NOT NULL,           -- nombre del equipo dueño de este 11 (home o away)
            formation TEXT,
            player_number INTEGER,
            player_name TEXT,
            position TEXT,
            line INTEGER,
            slot INTEGER,
            loaded_at TEXT,
            UNIQUE(home_team, away_team, team, player_number)
        )
    """)
    conn.commit()


def load_lineup_file(filepath, home_team, away_team):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    create_lineups_table(conn)

    # Borra alineación previa de este cruce antes de recargar (por si hay cambio de última hora)
    conn.execute(
        "DELETE FROM lineups WHERE home_team = ? AND away_team = ?",
        (home_team, away_team),
    )

    now = datetime.now(timezone.utc).isoformat()
    for side_key in ("spain", "argentina"):  # TODO: generalizar keys al agregar más partidos
        if side_key not in data:
            continue
        team_block = data[side_key]
        for p in team_block["players"]:
            conn.execute(
                """INSERT INTO lineups
                   (home_team, away_team, team, formation, player_number,
                    player_name, position, line, slot, loaded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (home_team, away_team, team_block["team"], team_block["formation"],
                 p["number"], p["name"], p["position"], p["line"], p["slot"], now),
            )
    conn.commit()
    conn.close()


def get_lineup(home_team, away_team):
    """Devuelve dict {team_name: {formation, players: [...]}} o None si no hay alineación cargada."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM lineups WHERE home_team = ? AND away_team = ? ORDER BY team, line, slot",
        (home_team, away_team),
    ).fetchall()
    conn.close()

    if not rows:
        return None

    result = {}
    for r in rows:
        team = r["team"]
        result.setdefault(team, {"formation": r["formation"], "players": []})
        result[team]["players"].append({
            "number": r["player_number"], "name": r["player_name"],
            "position": r["position"], "line": r["line"], "slot": r["slot"],
        })
    return result


if __name__ == "__main__":
    # Uso manual: python data/load_lineups.py
    for fname in os.listdir(LINEUPS_DIR):
        if not fname.endswith(".json"):
            continue
        base = fname.replace(".json", "")
        home, away = base.split("_")  # ej "spain_argentina" -> home=spain, away=argentina
        load_lineup_file(os.path.join(LINEUPS_DIR, fname), home.capitalize(), away.capitalize())
        print(f"Cargado: {home} vs {away}")