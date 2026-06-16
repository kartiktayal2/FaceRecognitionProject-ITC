# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("SELECT * from visitor_logs")


# print(cur.fetchall())

# conn.close()

# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# SELECT name
# FROM sqlite_master
# WHERE type='table'
# """)

# print(cur.fetchall())

# conn.close()

import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())

for table in ["users", "stats", "visitor_logs"]:
    cur.execute(f"PRAGMA table_info({table})")
    print(table, cur.fetchall())


