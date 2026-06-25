# import sqlite3

# conn = sqlite3.connect("database.db")

# cur = conn.cursor()

# cur.execute("""
# CREATE TABLE IF NOT EXISTS users(
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT,
#     email TEXT,
#     face_encoding TEXT
# )
# """)

# conn.commit()
# conn.close()

# print("Database created")


# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# try:
#     cur.execute("""
#     ALTER TABLE users
#     ADD COLUMN visit_count INTEGER DEFAULT 0
#     """)
#     print("Column Added")
# except:
#     print("Column Already Exists")

# conn.commit()
# conn.close()


# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# CREATE TABLE IF NOT EXISTS stats(
#     id INTEGER PRIMARY KEY,
#     unknown_count INTEGER DEFAULT 0
# )
# """)

# cur.execute("""
# INSERT OR IGNORE INTO stats(id, unknown_count)
# VALUES(1,0)
# """)

# conn.commit()
# conn.close()

# print("Stats table created")



# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("""
# CREATE TABLE IF NOT EXISTS unknown_faces(
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     face_encoding TEXT,
#     visit_count INTEGER DEFAULT 1,
#     last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
# )
# """)

# conn.commit()
# conn.close()

# print("unknown_faces table created")

# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("SELECT COUNT(*) FROM unknown_faces")
# print(cur.fetchone())

# conn.close()



import sqlite3

conn = sqlite3.connect("database.db")

conn.execute("ALTER TABLE staff_faces ADD COLUMN visit_count INTEGER DEFAULT 0")

conn.commit()
conn.close()

print("Done! Column added successfully.")