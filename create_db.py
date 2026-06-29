from database import get_connection

conn = get_connection()
cur = conn.cursor()

# =====================================================
# REGISTERED CUSTOMERS
# =====================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150),
    phone VARCHAR(20),
    face_encoding TEXT NOT NULL,
    visit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# =====================================================
# UNKNOWN CUSTOMERS
# =====================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS unknown_customers (
    id SERIAL PRIMARY KEY,
    face_encoding TEXT NOT NULL,
    visit_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# =====================================================
# VISIT LOGS
# =====================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS visit_logs (
    id SERIAL PRIMARY KEY,
    customer_type VARCHAR(20) NOT NULL,
    customer_id INTEGER NOT NULL,
    visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# =====================================================
# DAILY STATISTICS
# =====================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS daily_statistics (
    stat_date DATE PRIMARY KEY,
    known_today INTEGER DEFAULT 0,
    unknown_today INTEGER DEFAULT 0,
    returning_unknown_today INTEGER DEFAULT 0
)
""")

# =====================================================
# DATABASE MIGRATION
# =====================================================

cur.execute("""
ALTER TABLE customers
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")



...
# =====================================================
# DATABASE MIGRATION
# =====================================================

cur.execute("""
ALTER TABLE customers
ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")

# =====================================================
# SYSTEM SETTINGS
# =====================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,

    new_face_delay INTEGER DEFAULT 3,
    cooldown_seconds INTEGER DEFAULT 10,
    pending_expire_seconds INTEGER DEFAULT 8,

    known_threshold REAL DEFAULT 0.45,
    unknown_threshold REAL DEFAULT 0.40,

    dashboard_refresh_seconds INTEGER DEFAULT 5,
    auto_delete_logs_days INTEGER DEFAULT 3,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
INSERT INTO system_settings (
    id,
    new_face_delay,
    cooldown_seconds,
    pending_expire_seconds,
    known_threshold,
    unknown_threshold,
    dashboard_refresh_seconds,
    auto_delete_logs_days
)
SELECT
    1,
    3,
    10,
    8,
    0.45,
    0.40,
    5,
    3
WHERE NOT EXISTS (
    SELECT 1 FROM system_settings WHERE id = 1
);
""")

conn.commit()

cur.close()
conn.close()

print("ITC PostgreSQL database created successfully!")