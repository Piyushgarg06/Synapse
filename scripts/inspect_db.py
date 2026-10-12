import sqlite3

con = sqlite3.connect(r".synapse/index.db")
cur = con.cursor()

# Tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("=== TABLES ===")
print(tables)

print("\n=== SCHEMA ===")
for t in tables:
    cur.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,))
    row = cur.fetchone()
    if row:
        print(row[0])
        print()

print("\n=== SAMPLE: files ===")
cur.execute("SELECT * FROM files LIMIT 5")
cols = [d[0] for d in cur.description]
print(cols)
for r in cur.fetchall():
    print(r)

print("\n=== SAMPLE: symbols ===")
cur.execute("SELECT * FROM symbols LIMIT 8")
cols = [d[0] for d in cur.description]
print(cols)
for r in cur.fetchall():
    print(r)

print("\n=== SAMPLE: edges (call graph) ===")
cur.execute("SELECT * FROM edges LIMIT 8")
cols = [d[0] for d in cur.description]
print(cols)
for r in cur.fetchall():
    print(r)

print("\n=== COUNTS ===")
for t in tables:
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {cur.fetchone()[0]} rows")

con.close()
