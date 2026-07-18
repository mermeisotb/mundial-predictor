import numpy as np

from model.poisson_model import calculate_team_stats

N_SIMULATIONS = 10000


def simulate_match(home_team, away_team, n_simulations=N_SIMULATIONS, seed=None):
    """Simula el partido n_simulations veces usando los mismos lambda (goles
    esperados) que ya calcula el modelo Poisson, pero en vez de resolver la
    matriz analíticamente, sortea resultados individuales. Esto permite ver
    distribución completa: percentiles de goles, racha de resultados, etc.
    """
    stats, avg_goals_match = calculate_team_stats()

    if avg_goals_match is None or home_team not in stats or away_team not in stats:
        return None

    home = stats[home_team]
    away = stats[away_team]

    lambda_home = home["attack_strength"] * away["defense_strength"] * avg_goals_match
    lambda_away = away["attack_strength"] * home["defense_strength"] * avg_goals_match

    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(lambda_home, n_simulations)
    away_goals = rng.poisson(lambda_away, n_simulations)

    home_wins = int(np.sum(home_goals > away_goals))
    draws = int(np.sum(home_goals == away_goals))
    away_wins = int(np.sum(home_goals < away_goals))

    total_goals = home_goals + away_goals
    btts = int(np.sum((home_goals > 0) & (away_goals > 0)))

    # Marcadores más frecuentes en las simulaciones
    scorelines, counts = np.unique(
        np.stack([home_goals, away_goals], axis=1), axis=0, return_counts=True
    )
    top_idx = np.argsort(counts)[::-1][:5]
    top_scores = [
        ((int(scorelines[i][0]), int(scorelines[i][1])), round(counts[i] / n_simulations * 100, 1))
        for i in top_idx
    ]

    def pct(count):
        return round(count / n_simulations * 100, 1)

    return {
        "n_simulations": n_simulations,
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "home_win_prob": pct(home_wins),
        "draw_prob": pct(draws),
        "away_win_prob": pct(away_wins),
        "btts_prob": pct(btts),
        "over_1_5_prob": pct(int(np.sum(total_goals > 1))),
        "over_2_5_prob": pct(int(np.sum(total_goals > 2))),
        "over_3_5_prob": pct(int(np.sum(total_goals > 3))),
        "avg_total_goals": round(float(np.mean(total_goals)), 2),
        "goals_p10": int(np.percentile(total_goals, 10)),
        "goals_p50": int(np.percentile(total_goals, 50)),
        "goals_p90": int(np.percentile(total_goals, 90)),
        "top_scores": top_scores,
    }


if __name__ == "__main__":
    result = simulate_match("France", "England")
    if result:
        print(f"\n--- Monte Carlo: {result['n_simulations']} simulaciones ---")
        print(f"Gana local: {result['home_win_prob']}% | Empate: {result['draw_prob']}% | Gana visita: {result['away_win_prob']}%")
        print(f"Ambos anotan: {result['btts_prob']}%")
        print(f"Más de 1.5: {result['over_1_5_prob']}% | Más de 2.5: {result['over_2_5_prob']}% | Más de 3.5: {result['over_3_5_prob']}%")
        print(f"Goles totales — promedio: {result['avg_total_goals']}, p10: {result['goals_p10']}, p50: {result['goals_p50']}, p90: {result['goals_p90']}")
        print("Marcadores más frecuentes:")
        for score, prob in result["top_scores"]:
            print(f"  {score[0]}-{score[1]}: {prob}%")
    else:
        print("Sin datos suficientes.")