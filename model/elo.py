import sqlite3

DB_PATH = "data/db.sqlite"
K_FACTOR = 20  # qué tan rápido se ajusta el rating tras cada partido
BASE_RATING = 1500  # rating inicial para selecciones sin historial


def get_finished_matches():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score, utc_date
        FROM matches
        WHERE status = 'FINISHED'
        ORDER BY utc_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def expected_score(rating_a, rating_b):
    """Probabilidad esperada de que A le gane a B, según Elo"""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def actual_score(home_goals, away_goals):
    """1 = gana local, 0.5 = empate, 0 = gana visita"""
    if home_goals > away_goals:
        return 1.0, 0.0
    elif home_goals < away_goals:
        return 0.0, 1.0
    else:
        return 0.5, 0.5


def calculate_elo_ratings():
    matches = get_finished_matches()
    ratings = {}

    for home, away, home_goals, away_goals, date in matches:
        ratings.setdefault(home, BASE_RATING)
        ratings.setdefault(away, BASE_RATING)

        exp_home = expected_score(ratings[home], ratings[away])
        exp_away = 1 - exp_home

        actual_home, actual_away = actual_score(home_goals, away_goals)

        # ajuste extra por diferencia de goles (partidos goleados pesan más)
        goal_diff = abs(home_goals - away_goals)
        multiplier = 1 + (goal_diff - 1) * 0.15 if goal_diff > 1 else 1

        ratings[home] += K_FACTOR * multiplier * (actual_home - exp_home)
        ratings[away] += K_FACTOR * multiplier * (actual_away - exp_away)

    return ratings


if __name__ == "__main__":
    ratings = calculate_elo_ratings()
    ranked = sorted(ratings.items(), key=lambda x: x[1], reverse=True)

    print("--- Ranking Elo (basado en el Mundial actual) ---")
    for i, (team, rating) in enumerate(ranked[:15], 1):
        print(f"{i}. {team}: {round(rating, 1)}")