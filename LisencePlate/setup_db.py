import sqlite3

# Connect to SQLite database (creates one if not exists)
conn = sqlite3.connect('parking_system.db')
cursor = conn.cursor()

# Create a table for vehicle data
cursor.execute('''
CREATE TABLE IF NOT EXISTS vehicles (
    plate_number TEXT PRIMARY KEY,
    balance REAL
)
''')

print("Database and table created successfully!")

# Commit and close the connection
conn.commit()
conn.close()
