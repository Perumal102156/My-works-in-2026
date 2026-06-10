import sqlite3

conn = sqlite3.connect("tickets.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(tickets)")

for row in cursor.fetchall():
    print(row)

conn.close()