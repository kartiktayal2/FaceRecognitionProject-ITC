# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# SELECT COUNT(*)
# FROM unknown_faces
# """)

# print(cur.fetchone())

# conn.close()


# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# SELECT id, visit_count, last_seen
# FROM unknown_faces
# """)

# for row in cur.fetchall():
#     print(row)

# conn.close()

import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("SELECT * FROM stats")
print(cur.fetchall())

conn.close()

