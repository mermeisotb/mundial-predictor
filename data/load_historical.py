import sqlite3
import csv
import requests
from io import StringIO

DB_PATH = "data/db.sqlite"
CSV_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def download_csv():
    response = requests.get(CSV_URL)
    if response.status_code != 200:
        print(f"No se pudo descargar el CSV. Status: {response.status_code}")
        print("Verificá manualmente en https://github.com/martj42/international_results si el archivo sigue ahí.")
        return None
    return response.text


def load_into_db(csv_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_matches (
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            tournament TEXT
        )
    """)

    reader = csv.DictReader(StringIO(csv_text))
    count = 0
    for row in reader:
        try:
            cursor.execute("""
                INSERT INTO historical_matches (date, home_team, away_team, home_score, away_score, tournament)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                row["date"], row["home_team"], row["away_team"],
                int(row["home_score"]), int(row["away_score"]), row["tournament"]
            ))
            count += 1
        except (ValueError, KeyError):
            continue

    conn.commit()
    conn.close()
    print(f"{count} partidos históricos cargados en historical_matches.")


if __name__ == "__main__":
    print("Descargando histórico de partidos internacionales...")
    csv_text = download_csv()
    if csv_text:
        load_into_db(csv_text)