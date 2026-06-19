import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS staff_faces (
    staff_id INTEGER PRIMARY KEY,
    staff_code TEXT,
    name TEXT,
    face_encoding TEXT
)
""")

conn.commit()
conn.close()

print("staff_faces table created")