import sqlite3
from collections import defaultdict
from scipy.stats import poisson

DB_PATH = "data/db.sqlite"

DEFAULT_STATS = {"corners": 4.5, "yellow": 2.0, "matches": 5}

CORNER_LINES = [5.5, 7.5, 9.5]
CARD_LINES = [1.5, 2.5, 3.5]


def probability_to_fair_odds(probability):
    if probability <= 0:
        return None
    return round(100 / probability, 2)


def get_team_averages():
    """Promedios reales del Mundial 2026: córners desde kaggle_match_team_stats,
    tarjetas amarillas totales de la selección / partidos reales jugados por el equipo."""
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
            SELECT team_name, SUM(yellow_cards)
            FROM players
            GROUP BY team_name
        """)
        total_yellow_by_team = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        equipos = set(corners_rows) | set(total_yellow_by_team)
        for team in equipos:
            avg_corners, partidos_jugados = corners_rows.get(team, (4.5, 0))
            total_yellow = total_yellow_by_team.get(team, None)

            avg_yellow = (
                total_yellow / partidos_jugados
                if total_yellow and partidos_jugados
                else 2.0
            )
            averages[team] = {
                "corners": round(avg_corners, 2) if avg_corners else 4.5,
                "yellow": round(avg_yellow, 2),
                "matches": partidos_jugados,
            }
        return averages

    except sqlite3.OperationalError:
        return averages


def calculate_poisson_lines(lambda_value, lines):
    """Probabilidad de Over/Under para cada línea, usando una distribución
    de Poisson simple con el lambda combinado (local + visita)."""
    result = {}
    for line in lines:
        # line siempre termina en .5, así que floor(line) = cantidad de eventos
        # que hay que igualar o superar para el Over.
        threshold = int(line)
        over_prob = round((1 - poisson.cdf(threshold, lambda_value)) * 100, 1)
        under_prob = round(100 - over_prob, 1)
        result[line] = {
            "over_prob": over_prob,
            "under_prob": under_prob,
            "fair_odd_over": probability_to_fair_odds(over_prob),
            "fair_odd_under": probability_to_fair_odds(under_prob),
        }
    return result


def predict_corners_cards(home_team, away_team, averages):
    home = averages.get(home_team, DEFAULT_STATS)
    away = averages.get(away_team, DEFAULT_STATS)

    home_corners = home.get("corners", 4.5)
    away_corners = away.get("corners", 4.5)
    lambda_corners = home_corners + away_corners
    lambda_cards = home.get("yellow", 2.0) + away.get("yellow", 2.0)

    corner_lines = calculate_poisson_lines(lambda_corners, CORNER_LINES)
    card_lines = calculate_poisson_lines(lambda_cards, CARD_LINES)

    return {
        "home_expected_corners": round(home_corners, 1),
        "away_expected_corners": round(away_corners, 1),
        "expected_corners": round(lambda_corners, 1),
        "expected_cards": round(lambda_cards, 1),
        # se mantienen por compatibilidad con código que ya los use
        "over_9_5_corners_prob": corner_lines[9.5]["over_prob"],
        "over_3_5_cards_prob": card_lines[3.5]["over_prob"],
        "corner_lines": corner_lines,
        "card_lines": card_lines,
        "note": "Córners: promedio real Mundial 2026 (Kaggle). Tarjetas: estimado a partir del total de tarjetas por selección / partidos jugados.",
    }