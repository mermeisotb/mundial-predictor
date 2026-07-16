import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

# Usamos tu clave gratuita original de football-data.org
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
DB_PATH = "data/db.sqlite"

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_world_cup_matches():
    """Trae los partidos de la Copa del Mundo desde la API gratuita."""
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    url = f"{FOOTBALL_DATA_BASE}/competitions/WC/matches"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Error {response.status_code} al conectar con Football-Data: {response.text}")
            return None
        return response.json()
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None


def init_db():
    """Crea la tabla asegurando que existan las columnas de cuotas (vacías)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Reiniciamos la tabla para aplicar el esquema de forma limpia
    cursor.execute("DROP TABLE IF EXISTS matches")
    cursor.execute("""
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY,
            utc_date TEXT,
            stage TEXT,
            status TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            odd_home REAL,
            odd_draw REAL,
            odd_away REAL
        )
    """)
    conn.commit()
    return conn


def save_matches(matches):
    """Guarda los partidos reales y deja las cuotas listas en None para la app."""
    conn = init_db()
    cursor = conn.cursor()

    saved_count = 0
    for m in matches:
        home = m.get("homeTeam", {}).get("name")
        away = m.get("awayTeam", {}).get("name")

        # Filtro de seguridad para evitar partidos vacíos de rondas no definidas
        if not home or not away or home == "None" or away == "None":
            continue

        home_score = m["score"]["fullTime"]["home"]
        away_score = m["score"]["fullTime"]["away"]

        # Insertamos los partidos reales y configuramos las cuotas como NULL de forma segura
        cursor.execute("""
            INSERT OR REPLACE INTO matches
            (id, utc_date, stage, status, home_team, away_team, home_score, away_score, odd_home, odd_draw, odd_away)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
        """, (
            m["id"], m["utcDate"], m["stage"], m["status"],
            home, away, home_score, away_score
        ))
        saved_count += 1

    conn.commit()
    conn.close()
    print(f"✅ ¡Éxito! {saved_count} partidos reales guardados en {DB_PATH} (cuotas listas en None).")


if __name__ == "__main__":
    print("Trayendo partidos del Mundial usando la API gratuita (football-data.org)...")
    data = get_world_cup_matches()

    if data:
        matches = data.get("matches", [])
        save_matches(matches)

        finished = [m for m in matches if m["status"] == "FINISHED"]
        upcoming = [m for m in matches if m["status"] in ("SCHEDULED", "TIMED")]
        print(f"⚽ Sincronizados -> Finalizados: {len(finished)} | Próximos: {len(upcoming)}")
    else:
        print("❌ Sincronización fallida. Verifica la clave FOOTBALL_DATA_KEY en tu archivo .env")