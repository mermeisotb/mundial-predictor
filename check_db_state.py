import sqlite3

conn = sqlite3.connect("data/db.sqlite")

def contar(tabla, condicion=""):
    try:
        q = f"SELECT COUNT(*) FROM {tabla}"
        if condicion:
            q += f" WHERE {condicion}"
        return conn.execute(q).fetchone()[0]
    except sqlite3.OperationalError as e:
        return f"ERROR: {e}"

print("worldcup26_matches (total):", contar("worldcup26_matches"))
print("worldcup26_matches (finalizados):", contar("worldcup26_matches", "finished = 'TRUE'"))
print("worldcup26_matches (final/third):", contar("worldcup26_matches", "stage IN ('final','third')"))
print("players:", contar("players"))
print("kaggle_matches:", contar("kaggle_matches"))
print("historical_matches:", contar("historical_matches"))

conn.close()