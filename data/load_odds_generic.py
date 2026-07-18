"""
Carga cuotas reales desde un CSV genérico (exportado por Gemini/Claude en Chrome
u otra fuente) a data/db.sqlite. Formato esperado del CSV:

home_team,away_team,market,selection,odd

Carga: 1x2 (match_odds), goles over/under (goals_odds), córners over/under
(corners_odds), tarjetas over/under (cards_odds), ambos anotan (btts_odds).

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
MERCADOS_CORNERS = {"córners más/menos", "corners más/menos", "corners mas/menos"}
MERCADOS_TARJETAS = {"tarjetas totales más/menos", "tarjetas totales mas/menos"}
MERCADOS_BTTS = {"ambos equipos anotan"}


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


def es_si(selection):
    return selection.strip().lower() in ("yes", "sí", "si")


def es_no(selection):
    return selection.strip().lower() == "no"


def parse_over_under(filas_mercado):
    """Agrupa filas de un mercado over/under por línea numérica."""
    por_linea = defaultdict(dict)
    for market, selection, odd in filas_mercado:
        match = re.search(r"(\d+\.?\d*)", selection)
        if not match:
            continue
        line = float(match.group(1))
        sel_lower = selection.lower()
        if "over" in sel_lower or "más" in sel_lower or "mas" in sel_lower:
            por_linea[line]["over"] = odd
        elif "under" in sel_lower or "menos" in sel_lower:
            por_linea[line]["under"] = odd
    return por_linea


def setup_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS match_odds (
        home_team TEXT, away_team TEXT, odd_home REAL, odd_draw REAL, odd_away REAL,
        bookmakers_count INTEGER, last_update TEXT)""")
    for tabla in ("goals_odds", "corners_odds", "cards_odds"):
        conn.execute(f"""CREATE TABLE IF NOT EXISTS {tabla} (
            home_team TEXT, away_team TEXT, line REAL, odd_over REAL, odd_under REAL, last_update TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS btts_odds (
        home_team TEXT, away_team TEXT, odd_yes REAL, odd_no REAL, last_update TEXT)""")


def guardar_over_under(conn, tabla, home, away, por_linea, now):
    n = 0
    for line, valores in por_linea.items():
        if "over" in valores and "under" in valores:
            conn.execute(f"DELETE FROM {tabla} WHERE home_team=? AND away_team=? AND line=?", (home, away, line))
            conn.execute(f"""INSERT INTO {tabla} (home_team, away_team, line, odd_over, odd_under, last_update)
                VALUES (?, ?, ?, ?, ?, ?)""", (home, away, line, valores["over"], valores["under"], now))
            n += 1
    return n


def main():
    if len(sys.argv) != 2:
        print("Uso: python data/load_odds_generic.py <archivo.csv>")
        return

    with open(sys.argv[1], encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("[!] El CSV está vacío.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    setup_tables(conn)

    partidos = defaultdict(list)
    for r in rows:
        partidos[(r["home_team"].strip(), r["away_team"].strip())].append(r)

    resumen = defaultdict(int)

    for (home, away), filas in partidos.items():
        odd_home = odd_draw = odd_away = None
        odd_yes = odd_no = None
        filas_goles, filas_corners, filas_tarjetas = [], [], []

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
                filas_goles.append((market, selection, odd))
            elif market in MERCADOS_CORNERS:
                filas_corners.append((market, selection, odd))
            elif market in MERCADOS_TARJETAS:
                filas_tarjetas.append((market, selection, odd))
            elif market in MERCADOS_BTTS:
                if es_si(selection):
                    odd_yes = odd
                elif es_no(selection):
                    odd_no = odd

        if odd_home and odd_draw and odd_away:
            conn.execute("DELETE FROM match_odds WHERE home_team=? AND away_team=?", (home, away))
            conn.execute("""INSERT INTO match_odds VALUES (?, ?, ?, ?, ?, 1, ?)""",
                         (home, away, odd_home, odd_draw, odd_away, now))
            resumen["1x2"] += 1

        resumen["goles"] += guardar_over_under(conn, "goals_odds", home, away, parse_over_under(filas_goles), now)
        resumen["corners"] += guardar_over_under(conn, "corners_odds", home, away, parse_over_under(filas_corners), now)
        resumen["tarjetas"] += guardar_over_under(conn, "cards_odds", home, away, parse_over_under(filas_tarjetas), now)

        if odd_yes and odd_no:
            conn.execute("DELETE FROM btts_odds WHERE home_team=? AND away_team=?", (home, away))
            conn.execute("INSERT INTO btts_odds VALUES (?, ?, ?, ?, ?)", (home, away, odd_yes, odd_no, now))
            resumen["btts"] += 1

    conn.commit()
    conn.close()
    print(f"Cargado: {dict(resumen)}")


if __name__ == "__main__":
    main()