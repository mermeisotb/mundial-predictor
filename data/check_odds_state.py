"""Muestra el estado actual de las cuotas cargadas en db.sqlite para un
cruce, desglosado por casa de apuestas, con fecha de ultima actualizacion.

Uso: py -3 data/check_odds_state.py Spain Argentina
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

    print(f"\n=== match_odds (1X2) — {home} vs {away} ===")
    for row in conn.execute(
        "SELECT bookmaker, odd_home, odd_draw, odd_away, last_update FROM match_odds "
        "WHERE home_team = ? AND away_team = ? ORDER BY bookmaker",
        (home, away),
    ):
        print(row)

    for table, label in [("goals_odds", "Goles"), ("corners_odds", "Corners"), ("cards_odds", "Tarjetas")]:
        print(f"\n=== {table} ({label}) — {home} vs {away} ===")
        for row in conn.execute(
            f"SELECT bookmaker, line, odd_over, odd_under, last_update FROM {table} "
            "WHERE home_team = ? AND away_team = ? ORDER BY bookmaker, line",
            (home, away),
        ):
            print(row)

    print(f"\n=== btts_odds — {home} vs {away} ===")
    for row in conn.execute(
        "SELECT bookmaker, odd_yes, odd_no, last_update FROM btts_odds "
        "WHERE home_team = ? AND away_team = ? ORDER BY bookmaker",
        (home, away),
    ):
        print(row)

    conn.close()


if __name__ == "__main__":
    main()