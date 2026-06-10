import sqlite3

conn = sqlite3.connect('tickets.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT,
    name TEXT,
    designation TEXT,
    issue TEXT,
    description TEXT,
    status TEXT,
    resolution_notes TEXT
)
''')

conn.commit()
conn.close()

print("Database Created Successfully")