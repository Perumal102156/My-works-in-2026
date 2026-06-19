import sqlite3
import pymysql

sqlite_conn = sqlite3.connect("tickets.db")
sqlite_cursor = sqlite_conn.cursor()

mysql_conn = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="ticketing_db"
)
mysql_cursor = mysql_conn.cursor()

sqlite_cursor.execute("""
    SELECT ticket_id, name, designation, issue, description, status, resolution_notes
    FROM tickets
""")

rows = sqlite_cursor.fetchall()

for row in rows:
    mysql_cursor.execute("""
        INSERT INTO tickets
        (ticket_id, name, designation, issue, description, status, resolution_notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, row)

mysql_conn.commit()

sqlite_conn.close()
mysql_conn.close()

print("Migration completed. Total tickets moved:", len(rows))