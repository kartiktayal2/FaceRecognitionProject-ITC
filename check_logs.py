import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
SELECT id,user_name,visit_time
FROM visitor_logs
ORDER BY id DESC
LIMIT 10
""")

rows = cur.fetchall()

for row in rows:
    print(row)

conn.close()