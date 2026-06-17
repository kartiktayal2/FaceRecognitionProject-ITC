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



# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
# print(cur.fetchall())

# for table in ["users", "stats", "visitor_logs"]:
#     cur.execute(f"PRAGMA table_info({table})")
#     print(table, cur.fetchall())




# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# SELECT COUNT(*)
# FROM visitor_logs
# """)

# print("Total Logs =", cur.fetchone()[0])

# conn.close()


# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# SELECT visit_time
# FROM visitor_logs
# ORDER BY visit_time ASC
# LIMIT 5
# """)

# rows = cur.fetchall()

# for row in rows:
#     print(row)

# conn.close()

import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(unknown_faces)")
print(cur.fetchall())

conn.close()