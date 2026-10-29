import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute("INSERT INTO campaigns (name) VALUES (?)", ("IT",))
cursor.execute("INSERT INTO campaigns (name) VALUES (?)", ("Sales",))
cursor.execute("INSERT INTO campaigns (name) VALUES (?)", ("Support",))

conn.commit()
conn.close()

print("Campaigns added")