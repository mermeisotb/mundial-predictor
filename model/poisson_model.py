import sqlite3
from scipy.stats import poisson

DB_PATH = "data/db.sqlite"
MAX_GOALS = 6  # tope de goles a simular por equipo
GOAL_LINES = [0.5, 1.5, 2.5, 3.5, 4.5]
XG_WEIGHT = 0.4  # peso del xG real sobre el lambda Poisson cuando hay dato disponible


def probability_to_fair_odds(probability):
    """Converts a percentage probability into decimal fair odds."""
    if probability <= 0:
        return None
    return round(100 / probability, 2)


def calculate_goal_lines(score_matrix, total_probability):
    """Probabilidad de Over/Under para cada línea de goles totales del partido."""
    lines = {}
    for line in GOAL_LINES:
        over = sum(p for (h, a), p in score_matrix.items() if h + a > line) / total_probability
        over_prob = round(over * 100, 1)
        under_prob = round(100 - over_prob, 1)
        lines[line] = {
            "over_prob": over_prob,
            "under_prob": under_prob,
            "fair_odd_over": probability_to_fair_odds(over_prob),
            "fair_odd_under": probability_to_fair_odds(under_prob),
        }
    return lines


def get_finished_matches():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    rows = []

    try:
        cursor.execute("""
            SELECT home_team, away_team, home_score, away_score
            FROM matches
            WHERE status = 'FINISHED'
        """)
        rows.extend(cursor.fetchall())
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("""
            SELECT home_team, away_team, home_score, away_score
            FROM historical_matches
        """)
        rows.extend(cursor.fetchall())
    except sqlite3.OperationalError:
        pass

    conn.close()
    return rows


def calculate_team_stats():
    """Calcula promedio de goles anotados/recibidos por equipo, y fuerza de ataque/defensa relativa"""
    matches = get_finished_matches()

    if not matches:
        return {}, None

    goals_for = {}
    goals_against = {}
    games_played = {}

    for home, away, hg, ag in matches:
        for team in (home, away):
            goals_for.setdefault(team, 0)
            goals_against.setdefault(team, 0)
            games_played.setdefault(team, 0)

        goals_for[home] += hg
        goals_against[home] += ag
        games_played[home] += 1

        goals_for[away] += ag
        goals_against[away] += hg
        games_played[away] += 1

    avg_goals_match = sum(hg + ag for _, _, hg, ag in matches) / (2 * len(matches))

    stats = {}
    for team in games_played:
        gp = games_played[team]
        avg_scored = goals_for[team] / gp
        avg_conceded = goals_against[team] / gp

        stats[team] = {
            "avg_scored": avg_scored,
            "avg_conceded": avg_conceded,
            "attack_strength": avg_scored / avg_goals_match,
            "defense_strength": avg_conceded / avg_goals_match,
            "games_played": gp,
        }

    return stats, avg_goals_match


def get_team_recent_xg(team_name):
    """xG real más reciente del equipo, desde kaggle_match_prediction_features
    (prev_avg_xg_scored). Busca la fila más nueva donde el equipo aparezca
    como local o visita. Devuelve None si no hay dato."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT home_prev_avg_xg_scored, date FROM kaggle_match_prediction_features
            WHERE home_team_name = ? AND home_prev_avg_xg_scored IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """, (team_name,))
        home_row = cursor.fetchone()

        cursor.execute("""
            SELECT away_prev_avg_xg_scored, date FROM kaggle_match_prediction_features
            WHERE away_team_name = ? AND away_prev_avg_xg_scored IS NOT NULL
            ORDER BY date DESC LIMIT 1
        """, (team_name,))
        away_row = cursor.fetchone()

        conn.close()
    except sqlite3.OperationalError:
        return None

    candidates = [r for r in (home_row, away_row) if r]
    if not candidates:
        return None

    xg_value, _ = max(candidates, key=lambda r: r[1])
    try:
        return float(xg_value)
    except (TypeError, ValueError):
        return None


def calculate_expected_goals(home_team, away_team, lambda_home, lambda_away):
    """Combina el lambda Poisson (histórico goles) con el xG real reciente
    (Kaggle) cuando está disponible. Si no hay xG cargado para un equipo,
    ese lado usa directamente el lambda Poisson."""
    xg_home = get_team_recent_xg(home_team)
    xg_away = get_team_recent_xg(away_team)

    expected_home = (lambda_home * (1 - XG_WEIGHT) + xg_home * XG_WEIGHT) if xg_home is not None else lambda_home
    expected_away = (lambda_away * (1 - XG_WEIGHT) + xg_away * XG_WEIGHT) if xg_away is not None else lambda_away

    return {
        "poisson_home": round(lambda_home, 2),
        "poisson_away": round(lambda_away, 2),
        "xg_home": round(xg_home, 2) if xg_home is not None else None,
        "xg_away": round(xg_away, 2) if xg_away is not None else None,
        "expected_home": round(expected_home, 2),
        "expected_away": round(expected_away, 2),
        "expected_total": round(expected_home + expected_away, 2),
        "has_real_xg": xg_home is not None or xg_away is not None,
    }


def predict_match(home_team, away_team):
    stats, avg_goals_match = calculate_team_stats()

    if avg_goals_match is None or home_team not in stats or away_team not in stats:
        print(f"Sin datos suficientes para {home_team} o {away_team}")
        return None

    home = stats[home_team]
    away = stats[away_team]

    lambda_home = home["attack_strength"] * away["defense_strength"] * avg_goals_match
    lambda_away = away["attack_strength"] * home["defense_strength"] * avg_goals_match

    score_matrix = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            prob = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
            score_matrix[(h, a)] = prob

    home_win = sum(p for (h, a), p in score_matrix.items() if h > a)
    draw = sum(p for (h, a), p in score_matrix.items() if h == a)
    away_win = sum(p for (h, a), p in score_matrix.items() if h < a)

    total_probability = home_win + draw + away_win
    home_win /= total_probability
    draw /= total_probability
    away_win /= total_probability

    btts = sum(p for (h, a), p in score_matrix.items() if h > 0 and a > 0) / total_probability
    over_2_5 = sum(p for (h, a), p in score_matrix.items() if h + a > 2.5) / total_probability
    goal_lines = calculate_goal_lines(score_matrix, total_probability)
    expected_goals = calculate_expected_goals(home_team, away_team, lambda_home, lambda_away)

    top_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)[:5]

    home_win_prob = round(home_win * 100, 1)
    draw_prob = round(draw * 100, 1)
    away_win_prob = round(away_win * 100, 1)

    return {
        "home_team": home_team,
        "away_team": away_team,
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "home_win_prob": home_win_prob,
        "draw_prob": draw_prob,
        "away_win_prob": away_win_prob,
        "fair_odds": {
            "home": probability_to_fair_odds(home_win_prob),
            "draw": probability_to_fair_odds(draw_prob),
            "away": probability_to_fair_odds(away_win_prob),
        },
        "btts_prob": round(btts * 100, 1),
        "over_2_5_prob": round(over_2_5 * 100, 1),
        "goal_lines": goal_lines,
        "expected_goals": expected_goals,
        "top_scores": [(score, round(p * 100, 1)) for score, p in top_scores],
    }


if __name__ == "__main__":
    result = predict_match("Argentina", "England")

    if result:
        print(f"\n--- {result['home_team']} vs {result['away_team']} ---")
        print(f"Goles esperados: {result['home_team']} {result['lambda_home']} - {result['lambda_away']} {result['away_team']}")
        eg = result["expected_goals"]
        print(f"\nExpected Goals combinado (Poisson + xG real):")
        print(f"  {result['home_team']}: {eg['expected_home']} (Poisson {eg['poisson_home']} / xG real {eg['xg_home']})")
        print(f"  {result['away_team']}: {eg['expected_away']} (Poisson {eg['poisson_away']} / xG real {eg['xg_away']})")
        print(f"  Total esperado: {eg['expected_total']}")
        print(f"\nProbabilidades:")
        print(f"  Gana {result['home_team']}: {result['home_win_prob']}%")
        print(f"  Empate: {result['draw_prob']}%")
        print(f"  Gana {result['away_team']}: {result['away_win_prob']}%")
        print(f"  Ambos anotan: {result['btts_prob']}%")
        print(f"\nLíneas de goles:")
        for line, data in result['goal_lines'].items():
            print(f"  Más de {line}: {data['over_prob']}% (cuota {data['fair_odd_over']}) / "
                  f"Menos de {line}: {data['under_prob']}% (cuota {data['fair_odd_under']})")
        print(f"\nMarcadores más probables:")
        for (h, a), prob in result['top_scores']:
            print(f"  {h}-{a}: {prob}%")