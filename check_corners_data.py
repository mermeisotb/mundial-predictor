import sqlite3

conn = sqlite3.connect("data/db.sqlite")

print("--- kaggle_match_team_stats para France/England ---")
rows = conn.execute("""
    SELECT team_name, corners FROM kaggle_match_team_stats
    WHERE team_name IN ('France', 'England')
""").fetchall()
for r in rows:
    print(r)

print("\n--- players: tarjetas para France/England ---")
rows2 = conn.execute("""
    SELECT team_name, SUM(yellow_cards), SUM(matches_played)
    FROM players WHERE team_name IN ('France', 'England')
    GROUP BY team_name
""").fetchall()
for r in rows2:
    print(r)

conn.close()