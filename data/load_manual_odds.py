"""
Lee los CSV de cuotas manuales (exportados con Gemini/Chrome) desde
data/manual_odds/ y los inserta/actualiza en db.sqlite, distinguiendo
la casa de apuestas de origen (columna bookmaker) para poder comparar
varias casas sin que se pisen entre si.

Formato esperado del CSV: home_team,away_team,market,selection,odd

El nombre de la casa se deduce del nombre del archivo (todo lo que va
despues del ultimo guion bajo, antes de .csv). Ejemplos:
    spain_argentina_betano.csv   -> bookmaker = "betano"
    spain_argentina_epicbet.csv  -> bookmaker = "epicbet"
Si el archivo no sigue ese patron, se usa "generico".

Mercados reconocidos:
  - "Resultado del partido"                 -> match_odds (1X2)
  - cualquier mercado con "goles totales"    -> goals_odds (Over/Under X.X)
  - cualquier mercado con "corners totales"  -> corners_odds (Over/Under X.X)
  - cualquier mercado con "tarjetas totales" -> cards_odds (Over/Under X.X)
  - "ambos marcan" / "ambas equipos marcan" / "btts"
                                              -> btts_odds (Si/No)

Uso:
    py -3 data/load_manual_odds.py                       -> procesa todos los CSV en data/manual_odds/
    py -3 data/load_manual_odds.py spain_argentina_betano.csv  -> procesa solo ese archivo
"""

import csv
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

DB_PATH = "data/db.sqlite"
ODDS_DIR = Path("data/manual_odds")

MATCH_RESULT_MARKET = "resultado del partido"

GOALS_KEYWORDS = ["goles totales", "total de goles"]
CORNERS_KEYWORDS = ["corners totales", "córners totales", "total de corners", "total de córners"]
CARDS_KEYWORDS = ["tarjetas totales", "total de tarjetas"]
BTTS_KEYWORDS = ["ambos marcan", "ambas equipos marcan", "btts", "los dos equipos marcan"]

KNOWN_BOOKMAKERS = ["betano", "epicbet"]


def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def normalize_market(market_name):
    return strip_accents(market_name.strip().lower())


def detect_bookmaker(filename):
    stem = filename.lower()
    for name in KNOWN_BOOKMAKERS:
        if name in stem:
            return name
    # fallback: toma lo que hay despues del ultimo guion bajo
    match = re.search(r"_([a-z0-9]+)$", Path(stem).stem)
    return match.group(1) if match else "generico"


def ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_odds (
            home_team TEXT, away_team TEXT, bookmaker TEXT,
            odd_home REAL, odd_draw REAL, odd_away REAL,
            last_update TEXT
        )
    """)
    for table in ("goals_odds", "corners_odds", "cards_odds"):
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                home_team TEXT, away_team TEXT, bookmaker TEXT,
                line REAL, odd_over REAL, odd_under REAL,
                last_update TEXT
            )
        """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS btts_odds (
            home_team TEXT, away_team TEXT, bookmaker TEXT,
            odd_yes REAL, odd_no REAL,
            last_update TEXT
        )
    """)
    # Migracion suave: si las tablas ya existian sin columna bookmaker, la agrega.
    for table in ("match_odds", "goals_odds", "corners_odds", "cards_odds", "btts_odds"):
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
        if "bookmaker" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN bookmaker TEXT DEFAULT 'generico'")
    conn.commit()


def load_csv_rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def process_over_under_market(conn, table, home, away, bookmaker, rows, keywords, now, label):
    market_rows = [r for r in rows if any(k in normalize_market(r["market"]) for k in keywords)]
    if not market_rows:
        print(f"  [{label}] sin filas en el CSV, se omite")
        return

    lines_found = {}
    for r in market_rows:
        selection = r["selection"].strip()
        parts = selection.split()
        if len(parts) != 2:
            continue
        side, line_str = parts
        try:
            line = float(line_str)
        except ValueError:
            continue
        lines_found.setdefault(line, {})[side.lower()] = float(r["odd"])

    if not lines_found:
        print(f"  [{label}] filas encontradas pero no se pudo parsear ninguna línea (revisa formato 'Over X.X')")
        return

    deleted = conn.execute(
        f"DELETE FROM {table} WHERE home_team = ? AND away_team = ? AND bookmaker = ?",
        (home, away, bookmaker),
    ).rowcount
    for line, sides in sorted(lines_found.items()):
        odd_over = sides.get("over")
        odd_under = sides.get("under")
        conn.execute(
            f"INSERT INTO {table} (home_team, away_team, bookmaker, line, odd_over, odd_under, last_update) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (home, away, bookmaker, line, odd_over, odd_under, now),
        )
        print(f"  [{label} · {bookmaker}] {line}: Over {odd_over} / Under {odd_under}")
    print(f"  [{label} · {bookmaker}] {deleted} fila(s) vieja(s) borrada(s), {len(lines_found)} línea(s) nueva(s)")


def process_file(conn, path):
    rows = load_csv_rows(path)
    if not rows:
        print(f"  [vacio] {path.name}")
        return

    home = rows[0]["home_team"].strip()
    away = rows[0]["away_team"].strip()
    bookmaker = detect_bookmaker(path.name)
    now = datetime.now().isoformat()

    print(f"  Casa de apuestas detectada: {bookmaker}")

    # --- 1X2 ---
    result_rows = [r for r in rows if normalize_market(r["market"]) == MATCH_RESULT_MARKET]
    if result_rows:
        odds = {r["selection"].strip(): float(r["odd"]) for r in result_rows}
        odd_home = odds.get(home)
        odd_draw = odds.get("Draw") or odds.get("Empate")
        odd_away = odds.get(away)
        if odd_home and odd_draw and odd_away:
            deleted = conn.execute(
                "DELETE FROM match_odds WHERE home_team = ? AND away_team = ? AND bookmaker = ?",
                (home, away, bookmaker),
            ).rowcount
            conn.execute(
                "INSERT INTO match_odds (home_team, away_team, bookmaker, odd_home, odd_draw, odd_away, last_update) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (home, away, bookmaker, odd_home, odd_draw, odd_away, now),
            )
            print(f"  [1X2 · {bookmaker}] actualizado ({deleted} fila(s) vieja(s) borrada(s)): "
                  f"{home} {odd_home} / Empate {odd_draw} / {away} {odd_away}")
        else:
            print(f"  [!] 1X2 incompleto para {home} vs {away} ({bookmaker}), se omite (revisa el CSV)")
            print(f"      Detectado: home={odd_home}, draw={odd_draw}, away={odd_away}")
            print(f"      Selections en el CSV: {list(odds.keys())}")
    else:
        print(f"  [1X2] sin filas 'Resultado del partido' en el CSV, se omite")

    # --- Goles / Corners / Tarjetas (Over/Under) ---
    process_over_under_market(conn, "goals_odds", home, away, bookmaker, rows, GOALS_KEYWORDS, now, "Goles")
    process_over_under_market(conn, "corners_odds", home, away, bookmaker, rows, CORNERS_KEYWORDS, now, "Corners")
    process_over_under_market(conn, "cards_odds", home, away, bookmaker, rows, CARDS_KEYWORDS, now, "Tarjetas")

    # --- Ambos anotan (BTTS) ---
    btts_rows = [r for r in rows if any(k in normalize_market(r["market"]) for k in BTTS_KEYWORDS)]
    if btts_rows:
        selections = {r["selection"].strip().lower(): float(r["odd"]) for r in btts_rows}
        odd_yes = selections.get("si") or selections.get("sí") or selections.get("yes")
        odd_no = selections.get("no")
        if odd_yes:
            conn.execute(
                "DELETE FROM btts_odds WHERE home_team = ? AND away_team = ? AND bookmaker = ?",
                (home, away, bookmaker),
            )
            conn.execute(
                "INSERT INTO btts_odds (home_team, away_team, bookmaker, odd_yes, odd_no, last_update) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (home, away, bookmaker, odd_yes, odd_no, now),
            )
            print(f"  [BTTS · {bookmaker}] Si: {odd_yes} / No: {odd_no}")
        else:
            print(f"  [!] BTTS encontrado pero no se pudo parsear 'Si'/'No', selections: {list(selections.keys())}")
    else:
        print(f"  [BTTS] sin filas en el CSV, se omite")

    conn.commit()
    print(f"  OK — {home} vs {away} ({bookmaker})\n")


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