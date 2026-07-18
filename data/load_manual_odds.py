"""
Lee los CSV de cuotas manuales (exportados con Gemini/Chrome) desde
data/manual_odds/ y los inserta/actualiza en db.sqlite.

Formato esperado del CSV: home_team,away_team,market,selection,odd

Uso:
    py -3 data/load_manual_odds.py                       -> procesa todos los CSV en data/manual_odds/
    py -3 data/load_manual_odds.py france_england.csv    -> procesa solo ese archivo
"""

import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = "data/db.sqlite"
ODDS_DIR = Path("data/manual_odds")

# Mercados de 1X2 que reconocemos (puede haber varios "casinos"/variantes,
# nos quedamos con "Resultado del partido" a secas, ignorando SuperCuotas
# u otras variantes promocionales que no son la línea estándar del mercado).
MATCH_RESULT_MARKET = "Resultado del partido"

# Líneas de goles: buscamos filas "Over X.X" / "Under X.X" dentro de
# cualquier mercado que contenga "Goles totales" en el nombre.
GOALS_MARKET_KEYWORD = "goles totales"


def ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_odds (
            home_team TEXT, away_team TEXT,
            odd_home REAL, odd_draw REAL, odd_away REAL,
            last_update TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals_odds (
            home_team TEXT, away_team TEXT,
            line REAL, odd_over REAL, odd_under REAL,
            last_update TEXT
        )
    """)
    conn.commit()


def load_csv_rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def process_file(conn, path):
    rows = load_csv_rows(path)
    if not rows:
        print(f"  [vacio] {path.name}")
        return

    home = rows[0]["home_team"].strip()
    away = rows[0]["away_team"].strip()
    now = datetime.now().isoformat()

    # --- 1X2 ---
    result_rows = [r for r in rows if r["market"].strip() == MATCH_RESULT_MARKET]
    if result_rows:
        odds = {r["selection"].strip(): float(r["odd"]) for r in result_rows}
        odd_home = odds.get(home)
        odd_draw = odds.get("Draw") or odds.get("Empate")
        odd_away = odds.get(away)
        if odd_home and odd_draw and odd_away:
            conn.execute("DELETE FROM match_odds WHERE home_team = ? AND away_team = ?", (home, away))
            conn.execute(
                "INSERT INTO match_odds (home_team, away_team, odd_home, odd_draw, odd_away, last_update) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (home, away, odd_home, odd_draw, odd_away, now),
            )
            print(f"  1X2 actualizado: {home} {odd_home} / Empate {odd_draw} / {away} {odd_away}")
        else:
            print(f"  [!] 1X2 incompleto para {home} vs {away}, se omite (revisa el CSV)")

    # --- Líneas de goles Over/Under ---
    goals_rows = [r for r in rows if GOALS_MARKET_KEYWORD in r["market"].strip().lower()]
    lines_found = {}
    for r in goals_rows:
        selection = r["selection"].strip()
        try:
            side, line_str = selection.split()
            line = float(line_str)
        except ValueError:
            continue
        lines_found.setdefault(line, {})[side.lower()] = float(r["odd"])

    conn.execute("DELETE FROM goals_odds WHERE home_team = ? AND away_team = ?", (home, away))
    for line, sides in sorted(lines_found.items()):
        odd_over = sides.get("over")
        odd_under = sides.get("under")
        conn.execute(
            "INSERT INTO goals_odds (home_team, away_team, line, odd_over, odd_under, last_update) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (home, away, line, odd_over, odd_under, now),
        )
        print(f"  Goles {line}: Over {odd_over} / Under {odd_under}")

    conn.commit()
    print(f"  OK — {home} vs {away}\n")


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)

    if len(sys.argv) > 1:
        files = [ODDS_DIR / sys.argv[1]]
    else:
        files = sorted(ODDS_DIR.glob("*.csv"))

    if not files:
        print(f"No se encontraron CSV en {ODDS_DIR}/")
        conn.close()
        return

    for path in files:
        if not path.exists():
            print(f"[!] No existe: {path}")
            continue
        print(f"Procesando {path.name}...")
        process_file(conn, path)

    conn.close()
    print("Listo.")


if __name__ == "__main__":
    main()