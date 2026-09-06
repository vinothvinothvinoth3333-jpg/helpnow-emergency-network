import sqlite3
import os

# Create database folder
database_folder = "database"
os.makedirs(database_folder, exist_ok=True)

# Database path
database_path = os.path.join(database_folder, "helpnow.db")

# Connect to database
connection = sqlite3.connect(database_path)

cursor = connection.cursor()


# =========================
# 1. USERS TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    role TEXT DEFAULT 'user',
    verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


# =========================
# 2. EMERGENCY REPORTS TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS emergency_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
)
""")


# =========================
# 3. HELPERS TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS helpers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    service_type TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    verified INTEGER DEFAULT 0,
    available INTEGER DEFAULT 1,

    FOREIGN KEY (user_id)
    REFERENCES users(id)
)
""")


# =========================
# 4. RESPONSES TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emergency_id INTEGER NOT NULL,
    helper_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (emergency_id)
    REFERENCES emergency_reports(id),

    FOREIGN KEY (helper_id)
    REFERENCES helpers(id)
)
""")


# Save changes
connection.commit()

# Close database
connection.close()

print("Database created successfully!")
print("All 4 tables created successfully!")