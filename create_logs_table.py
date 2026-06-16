# import sqlite3

# conn = sqlite3.connect("database.db")

# cur = conn.cursor()

# cur.execute("""
# CREATE TABLE IF NOT EXISTS visitor_logs(
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_name TEXT,
#     status TEXT,
#     visit_time DATETIME DEFAULT CURRENT_TIMESTAMP
# )
# """)

# conn.commit()
# conn.close()

# print("visitor_logs table created")

