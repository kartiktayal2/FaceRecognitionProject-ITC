from database import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("POSTGRESQL DATABASE INFORMATION")
print("=" * 80)

# Database Name
cur.execute("SELECT current_database();")
print("\nDatabase:", cur.fetchone()[0])

# PostgreSQL Version
cur.execute("SELECT version();")
print("\nPostgreSQL Version:")
print(cur.fetchone()[0])

print("\n" + "=" * 80)
print("TABLES")
print("=" * 80)

# Get all tables
cur.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema='public'
ORDER BY table_name;
""")

tables = [row[0] for row in cur.fetchall()]

for table in tables:

    print("\n" + "=" * 80)
    print(f"TABLE : {table}")
    print("=" * 80)

    # Columns
    cur.execute("""
    SELECT
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_name=%s
    ORDER BY ordinal_position;
    """, (table,))

    columns = cur.fetchall()

    print("\nColumns:")

    for col in columns:
        print(f"{col[0]:25} {col[1]}")

    # Row Count
    cur.execute(f"SELECT COUNT(*) FROM {table};")
    count = cur.fetchone()[0]

    print(f"\nTotal Rows : {count}")

    # Print Data
    cur.execute(f"SELECT * FROM {table};")
    rows = cur.fetchall()

    if len(rows) == 0:
        print("\nNo Data")
    else:
        print("\nData:")
        for row in rows:
            print(row)

print("\n" + "=" * 80)
print("END")
print("=" * 80)

cur.close()
conn.close()