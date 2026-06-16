import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("DELETE FROM users")

conn.commit()
conn.close()

print("Database cleared")