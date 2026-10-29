import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM campaigns")
print(cursor.fetchall())

conn.close()