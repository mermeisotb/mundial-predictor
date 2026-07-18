"""Muestra el estado actual de las cuotas cargadas en db.sqlite para un
cruce, con fecha de ultima actualizacion. Util para confirmar que un
load_manual_odds.py realmente escribio lo esperado.

Uso: py -3 data/check_odds_state.py France England
"""
import sqlite3
import sys

DB_PATH = "data/db.sqlite"


def main():
    if len(sys.argv) != 3:
        print("Uso: py -3 data/check_odds_state.py <Local> <Visita>")
        return

    home, away = sys.argv[1], sys.argv[2]
    conn = sqlite3.connect(DB_PATH)

    print(f"\n=== match_odds ({home} vs {away}) ===")
    for row in conn.execute(
        "SELECT odd_home, odd_draw, odd_away, last_update FROM match_odds "
        "WHERE home_team = ? AND away_team = ? ORDER BY last_update DESC",
        (home, away),
    ):
        print(row)

    print(f"\n=== goals_odds ({home} vs {away}) ===")
    for row in conn.execute(
        "SELECT line, odd_over, odd_under, last_update FROM goals_odds "
        "WHERE home_team = ? AND away_team = ? ORDER BY line",
        (home, away),
    ):
        print(row)

    conn.close()


if __name__ == "__main__":
    main()