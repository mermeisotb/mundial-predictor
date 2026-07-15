import sqlite3
from scipy.stats import poisson

DB_PATH = "data/db.sqlite"
MAX_GOALS = 6  # tope de goles a simular por equipo


def get_finished_matches():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT home_team, away_team, home_score, away_score
        FROM matches
        WHERE status = 'FINISHED'
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def calculate_team_stats():
    """Calcula promedio de goles anotados/recibidos por equipo, y fuerza de ataque/defensa relativa"""
    matches = get_finished_matches()

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


def predict_match(home_team, away_team):
    stats, avg_goals_match = calculate_team_stats()

    if home_team not in stats or away_team not in stats:
        print(f"Sin datos suficientes para {home_team} o {away_team}")
        return None

    home = stats[home_team]
    away = stats[away_team]

    # lambda = goles esperados, combinando ataque propio y defensa rival
    lambda_home = home["attack_strength"] * away["defense_strength"] * avg_goals_match
    lambda_away = away["attack_strength"] * home["defense_strength"] * avg_goals_match

    # matriz de probabilidades de marcador exacto
    score_matrix = {}
    for h in range(MAX_GOALS + 1):
        for a in range(MAX_GOALS + 1):
            prob = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
            score_matrix[(h, a)] = prob

    home_win = sum(p for (h, a), p in score_matrix.items() if h > a)
    draw = sum(p for (h, a), p in score_matrix.items() if h == a)
    away_win = sum(p for (h, a), p in score_matrix.items() if h < a)

    btts = sum(p for (h, a), p in score_matrix.items() if h > 0 and a > 0)
    over_2_5 = sum(p for (h, a), p in score_matrix.items() if h + a > 2.5)

    top_scores = sorted(score_matrix.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "home_team": home_team,
        "away_team": away_team,
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "home_win_prob": round(home_win * 100, 1),
        "draw_prob": round(draw * 100, 1),
        "away_win_prob": round(away_win * 100, 1),
        "btts_prob": round(btts * 100, 1),
        "over_2_5_prob": round(over_2_5 * 100, 1),
        "top_scores": [(score, round(p * 100, 1)) for score, p in top_scores],
    }


if __name__ == "__main__":
    result = predict_match("Argentina", "England")

    if result:
        print(f"\n--- {result['home_team']} vs {result['away_team']} ---")
        print(f"Goles esperados: {result['home_team']} {result['lambda_home']} - {result['lambda_away']} {result['away_team']}")
        print(f"\nProbabilidades:")
        print(f"  Gana {result['home_team']}: {result['home_win_prob']}%")
        print(f"  Empate: {result['draw_prob']}%")
        print(f"  Gana {result['away_team']}: {result['away_win_prob']}%")
        print(f"  Ambos anotan: {result['btts_prob']}%")
        print(f"  Más de 2.5 goles: {result['over_2_5_prob']}%")
        print(f"\nMarcadores más probables:")
        for (h, a), prob in result['top_scores']:
            print(f"  {h}-{a}: {prob}%")