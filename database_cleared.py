# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# cur.execute("DELETE FROM users")

# conn.commit()
# conn.close()

# print("Database cleared")

# import sqlite3

# conn = sqlite3.connect("database.db")
# cur = conn.cursor()

# # Check who is registered
# cur.execute("SELECT staff_id, name FROM staff_faces")
# rows = cur.fetchall()

# print("Registered faces:")
# for row in rows:
#     print(f"  ID: {row[0]} | Name: {row[1]}")

# # Change this name to whoever you want to delete
# name_to_delete = "kar demo"

# cur.execute("DELETE FROM staff_faces WHERE name = ?", (name_to_delete,))
# conn.commit()

# print(f"\nDeleted: {name_to_delete}")
# print(f"Rows deleted: {cur.rowcount}")

# conn.close()


import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("DELETE FROM unknown_faces")
cur.execute("UPDATE stats SET unknown_count = 0 WHERE id = 1")

conn.commit()
conn.close()

print("Done! All unknown faces deleted and count reset to 0.")