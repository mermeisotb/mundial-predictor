"""
Carga cuotas reales desde un CSV genérico (exportado por Gemini/Claude en Chrome
u otra fuente) a data/db.sqlite. Formato esperado del CSV:

home_team,away_team,market,selection,odd
France,England,Resultado del partido,France,1.91
France,England,Resultado del partido,Draw,3.85
France,England,Resultado del partido,England,3.75
France,England,Goles totales Más/Menos,Over 2.5,1.47
France,England,Goles totales Más/Menos,Under 2.5,2.72

Por ahora carga solo 1x2 (tabla match_odds) y over/under de goles (tabla
goals_odds). Otros mercados (córners, tarjetas, ambos anotan) se ignoran
por el momento -- se integran más adelante.

Reconoce automáticamente cualquier equipo/partido presente en el archivo,
sin necesidad de pasar parámetros.

Uso: python data/load_odds_generic.py <archivo.csv>
"""

import csv
import re
import sys
import sqlite3
from collections import defaultdict
from datetime import datetime

DB_PATH = "data/db.sqlite"

MERCADOS_1X2 = {"resultado del partido"}
MERCADOS_GOLES = {"goles totales más/menos", "goles totales mas/menos"}


def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def es_local(selection, home):
    s = selection.strip().lower()
    return s == home.strip().lower() or s in ("1", "(1)") or home.strip().lower() in s


def es_visita(selection, away):
    s = selection.strip().lower()
    return s == away.strip().lower() or s in ("2", "(2)") or away.strip().lower() in s


def es_empate(selection):
    return selection.strip().lower() in ("draw", "empate", "x", "(x)")


def setup_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_odds (
            home_team TEXT, away_team TEXT, odd_home REAL, odd_draw REAL, odd_away REAL,
            bookmakers_count INTEGER, last_update TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS goals_odds (
            home_team TEXT, away_team TEXT, line REAL, odd_over REAL, odd_under REAL, last_update TEXT
        )
    """)


def main():
    if len(sys.argv) != 2:
        print("Uso: python data/load_odds_generic.py <archivo.csv>")
        return

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("[!] El CSV está vacío.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    setup_tables(conn)

    partidos = defaultdict(list)
    for r in rows:
        home, away = r["home_team"].strip(), r["away_team"].strip()
        partidos[(home, away)].append(r)

    resumen_1x2, resumen_goles = 0, 0

    for (home, away), filas in partidos.items():
        odd_home = odd_draw = odd_away = None
        goles_por_linea = defaultdict(dict)  # {2.5: {"over": x, "under": y}}

        for r in filas:
            market = r["market"].strip().lower()
            selection = r["selection"].strip()
            odd = to_float(r["odd"])
            if odd is None:
                continue

            if market in MERCADOS_1X2:
                if es_empate(selection):
                    odd_draw = odd
                elif es_local(selection, home):
                    odd_home = odd
                elif es_visita(selection, away):
                    odd_away = odd

            elif market in MERCADOS_GOLES:
                match = re.search(r"(\d+\.?\d*)", selection)
                if not match:
                    continue
                line = float(match.group(1))
                if "over" in selection.lower() or "más" in selection.lower() or "mas" in selection.lower():
                    goles_por_linea[line]["over"] = odd
                elif "under" in selection.lower() or "menos" in selection.lower():
                    goles_por_linea[line]["under"] = odd

        if odd_home and odd_draw and odd_away:
            conn.execute(
                "DELETE FROM match_odds WHERE home_team = ? AND away_team = ?", (home, away)
            )
            conn.execute("""
                INSERT INTO match_odds (home_team, away_team, odd_home, odd_draw, odd_away, bookmakers_count, last_update)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (home, away, odd_home, odd_draw, odd_away, now))
            resumen_1x2 += 1
            print(f"[OK] 1x2 {home} vs {away}: {odd_home} / {odd_draw} / {odd_away}")

        for line, valores in goles_por_linea.items():
            if "over" in valores and "under" in valores:
                conn.execute(
                    "DELETE FROM goals_odds WHERE home_team = ? AND away_team = ? AND line = ?",
                    (home, away, line),
                )
                conn.execute("""
                    INSERT INTO goals_odds (home_team, away_team, line, odd_over, odd_under, last_update)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (home, away, line, valores["over"], valores["under"], now))
                resumen_goles += 1
                print(f"[OK] Goles {home} vs {away} línea {line}: Over {valores['over']} / Under {valores['under']}")

    conn.commit()
    conn.close()
    print(f"\nResumen: {resumen_1x2} partido(s) 1x2, {resumen_goles} línea(s) de goles cargadas.")


if __name__ == "__main__":
    main()