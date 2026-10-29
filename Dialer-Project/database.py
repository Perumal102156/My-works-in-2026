import sqlite3

conn = sqlite3.connect('database.db')

cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    extension TEXT UNIQUE,
    password TEXT,
    status TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS campaigns (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT UNIQUE,

    call_type TEXT,

    caller_id TEXT,

    queue_name TEXT,

    crm TEXT,

    pause_codes TEXT,

    dial_ratio TEXT,

    wrap_time INTEGER,

    active TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS agent_campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER,
    campaign_id INTEGER
)
''')
cursor.execute('''
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    phone_number TEXT,
    campaign TEXT,
    call_status TEXT,
    disposition TEXT,
    notes TEXT,
    callback_date TEXT
)
''')
conn.commit()
conn.close()

print("Database Created Successfully")