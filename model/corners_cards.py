import sqlite3
from collections import defaultdict
from scipy.stats import poisson

DB_PATH = "data/db.sqlite"

DEFAULT_STATS = {"corners": 4.5, "yellow": 2.0, "matches": 5}


def get_team_averages():
    """Promedios reales del Mundial 2026: córners desde kaggle_match_team_stats,
    tarjetas amarillas estimadas desde players (total del torneo / partidos jugados)."""
    averages = defaultdict(lambda: DEFAULT_STATS)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT team_name, AVG(corners), COUNT(*)
            FROM kaggle_match_team_stats
            WHERE corners IS NOT NULL
            GROUP BY team_name
        """)
        corners_rows = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        cursor.execute("""
            SELECT team_name, SUM(yellow_cards), SUM(matches_played)
            FROM players
            GROUP BY team_name
        """)
        cards_rows = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

        conn.close()

        equipos = set(corners_rows) | set(cards_rows)
        for team in equipos:
            avg_corners, matches_c = corners_rows.get(team, (4.5, 0))
            total_yellow, total_matches = cards_rows.get(team, (None, None))
            avg_yellow = (
                total_yellow / total_matches
                if total_yellow and total_matches
                else 2.0
            )
            averages[team] = {
                "corners": round(avg_corners, 2) if avg_corners else 4.5,
                "yellow": round(avg_yellow, 2),
                "matches": matches_c or total_matches or 0,
            }
        return averages

    except sqlite3.OperationalError:
        return averages


def predict_corners_cards(home_team, away_team, averages):
    home = averages.get(home_team, DEFAULT_STATS)
    away = averages.get(away_team, DEFAULT_STATS)

    lambda_corners = home.get("corners", 4.5) + away.get("corners", 4.5)
    lambda_cards = home.get("yellow", 2.0) + away.get("yellow", 2.0)

    return {
        "expected_corners": round(lambda_corners, 1),
        "expected_cards": round(lambda_cards, 1),
        "over_9_5_corners_prob": round((1 - poisson.cdf(9, lambda_corners)) * 100, 1),
        "over_3_5_cards_prob": round((1 - poisson.cdf(3, lambda_cards)) * 100, 1),
        "note": "Córners: promedio real Mundial 2026 (Kaggle). Tarjetas: estimado a partir del total de tarjetas por selección / partidos jugados.",
    }