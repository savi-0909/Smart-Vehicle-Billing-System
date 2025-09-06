import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("parking_system.db")
cursor = conn.cursor()

# Drop existing tables (if needed)
cursor.execute("DROP TABLE IF EXISTS vehicles")
cursor.execute("DROP TABLE IF EXISTS checkins")
cursor.execute("DROP TABLE IF EXISTS logs")
cursor.execute("DROP TABLE IF EXISTS admins")

# Create tables again
cursor.execute('''CREATE TABLE IF NOT EXISTS vehicles (
    plate TEXT PRIMARY KEY,
    name TEXT,
    balance REAL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS checkins (
    plate TEXT PRIMARY KEY,
    checkin_time TEXT,
    admin TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
    plate TEXT,
    name TEXT,
    checkin TEXT,
    checkout TEXT,
    duration INTEGER,
    fee REAL,
    admin TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password TEXT
)''')

# Insert default admin users if they don't already exist
admins = [("admin1", "1234"), ("admin2", "5678")]
for admin in admins:
    cursor.execute("INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)", admin)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database has been reset with default admin users.")
