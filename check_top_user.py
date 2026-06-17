import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
SELECT user_name, COUNT(*)
FROM visitor_logs
GROUP BY user_name
ORDER BY COUNT(*) DESC
""")

rows = cur.fetchall()

for row in rows:
    print(row)

conn.close()