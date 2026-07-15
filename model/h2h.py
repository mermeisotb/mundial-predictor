import sqlite3

DB_PATH = "data/db.sqlite"
LAST_N = 5


def get_all_h2h(team_a, team_b):
    """Combina partidos del torneo actual + histórico, sin duplicar fuente"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT utc_date, home_team, away_team, home_score, away_score, stage
        FROM matches
        WHERE status = 'FINISHED'
        AND ((home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?))
    """, (team_a, team_b, team_b, team_a))
    current = cursor.fetchall()

    cursor.execute("""
        SELECT date, home_team, away_team, home_score, away_score, tournament
        FROM historical_matches
        WHERE (home_team = ? AND away_team = ?) OR (home_team = ? AND away_team = ?)
    """, (team_a, team_b, team_b, team_a))
    historical = cursor.fetchall()

    conn.close()

    all_matches = list(current) + list(historical)
    all_matches.sort(key=lambda x: x[0], reverse=True)  # más reciente primero
    return all_matches


def calculate_h2h_probability(team_a, team_b):
    matches = get_all_h2h(team_a, team_b)

    if not matches:
        return {
            "team_a": team_a,
            "team_b": team_b,
            "h2h_available": False,
            "note": "Sin enfrentamientos históricos registrados entre estas selecciones",
        }

    recent = matches[:LAST_N]

    wins_a = wins_b = draws = 0
    goals_a = goals_b = 0
    history = []

    for date, home, away, hg, ag, comp in recent:
        if home == team_a:
            ga, gb = hg, ag
        else:
            ga, gb = ag, hg

        goals_a += ga
        goals_b += gb

        if ga > gb:
            wins_a += 1
        elif ga < gb:
            wins_b += 1
        else:
            draws += 1

        history.append(f"{date} | {comp} | {home} {hg}-{ag} {away}")

    n = len(recent)
    # probabilidad empírica simple basada en frecuencia de resultados en los últimos N
    prob_a = round((wins_a / n) * 100, 1)
    prob_b = round((wins_b / n) * 100, 1)
    prob_draw = round((draws / n) * 100, 1)

    return {
        "team_a": team_a,
        "team_b": team_b,
        "h2h_available": True,
        "total_h2h_found": len(matches),
        "matches_used": n,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "avg_goals_a": round(goals_a / n, 2),
        "avg_goals_b": round(goals_b / n, 2),
        "prob_a_win_h2h": prob_a,
        "prob_b_win_h2h": prob_b,
        "prob_draw_h2h": prob_draw,
        "history": history,
    }


if __name__ == "__main__":
    result = calculate_h2h_probability("Argentina", "England")

    print(f"--- H2H: {result['team_a']} vs {result['team_b']} ---")

    if not result["h2h_available"]:
        print(result["note"])
    else:
        print(f"Enfrentamientos totales encontrados: {result['total_h2h_found']}")
        print(f"Usando últimos {result['matches_used']}:\n")
        for h in result["history"]:
            print(f"  {h}")

        print(f"\nVictorias {result['team_a']}: {result['wins_a']} ({result['prob_a_win_h2h']}%)")
        print(f"Victorias {result['team_b']}: {result['wins_b']} ({result['prob_b_win_h2h']}%)")
        print(f"Empates: {result['draws']} ({result['prob_draw_h2h']}%)")
        print(f"Promedio goles {result['team_a']}: {result['avg_goals_a']}")
        print(f"Promedio goles {result['team_b']}: {result['avg_goals_b']}")