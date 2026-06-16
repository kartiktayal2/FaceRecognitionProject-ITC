import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

# Reset visit count
cur.execute("""
UPDATE users
SET visit_count = 0
""")

# Clear visitor logs
cur.execute("""
DELETE FROM visitor_logs
""")

conn.commit()
conn.close()

print("Counts Reset Successfully")