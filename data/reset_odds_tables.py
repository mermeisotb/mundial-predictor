import sqlite3

conn = sqlite3.connect("data/db.sqlite")
conn.execute("DROP TABLE IF EXISTS match_odds")
conn.execute("DROP TABLE IF EXISTS goals_odds")
conn.commit()
conn.close()
print("Tablas eliminadas.")