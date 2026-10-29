import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
import random
import time
from threading import Thread
import pandas as pd
from flask import send_file

app = Flask(__name__)
app.secret_key = 'secret123'

socketio = SocketIO(app, async_mode='threading')

stats = {
    "agents": 11,
    "active_calls": 6,
    "waiting_calls": 2,
    "total_calls": 3102
}

USERNAME = "admin"
PASSWORD = "admin123"

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == USERNAME and password == PASSWORD:
            session['user'] = username
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html', stats=stats)

def update_stats():
    while True:
        stats['active_calls'] = random.randint(1, 15)
        stats['waiting_calls'] = random.randint(0, 10)
        stats['total_calls'] += random.randint(1, 5)

        socketio.emit('update', stats)

        time.sleep(5)

thread = Thread(target=update_stats)
thread.daemon = True
thread.start()
@app.route('/agents', methods=['GET', 'POST'])
def agents():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        extension = request.form['extension']
        password = request.form['password']
        status = request.form['status']

        try:
            cursor.execute(
                'INSERT INTO agents (name, extension, password, status) VALUES (?, ?, ?, ?)',
                (name, extension, password, status)
            )
            conn.commit()

            return redirect(url_for('agents'))

        except sqlite3.IntegrityError:
            return "Extension already exists"

    cursor.execute('SELECT * FROM agents')
    agents = cursor.fetchall()

    conn.close()

    return render_template('agents.html', agents=agents)
@app.route('/agent-login', methods=['GET', 'POST'])
def agent_login():

    if request.method == 'POST':

        extension = request.form['extension']
        password = request.form['password']
        campaign = request.form['campaign']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM agents WHERE extension=? AND password=?',
            (extension, password)
        )

        agent = cursor.fetchone()

        conn.close()

        if agent:
            session['agent'] = agent[1]
            session['campaign'] = campaign
            return redirect(url_for('agent_dashboard'))
        else:
            return "Invalid Login"

    return render_template('agent_login.html')
@app.route('/agent-dashboard', methods=['GET', 'POST'])
def agent_dashboard():

    if 'agent' not in session:
        return redirect(url_for('agent_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        customer_name = request.form['customer_name']
        phone_number = request.form['phone_number']
        campaign = request.form['campaign']
        call_status = request.form['call_status']
        disposition = request.form['disposition']
        notes = request.form['notes']
        callback_date = request.form['callback_date']

        cursor.execute('''
            INSERT INTO calls
            (customer_name, phone_number, campaign, call_status, disposition, notes, callback_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_name,
            phone_number,
            campaign,
            call_status,
            disposition,
            notes,
            callback_date
        ))

        conn.commit()

    cursor.execute("SELECT * FROM calls ORDER BY id DESC")
    calls = cursor.fetchall()

    conn.close()

    return render_template('agent_dashboard.html', calls=calls)

@app.route('/campaigns')
def campaigns():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM campaigns')

    campaigns = cursor.fetchall()

    conn.close()

    return render_template('campaigns.html', campaigns=campaigns)
@app.route('/create_campaign', methods=['GET', 'POST'])
def create_campaign():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']

        call_type = request.form['call_type']

        caller_id = request.form['caller_id']

        queue_name = request.form['queue_name']

        crm = request.form['crm']

        pause_codes = request.form['pause_codes']

        dial_ratio = request.form['dial_ratio']

        wrap_time = request.form['wrap_time']

        active = request.form['active']

        try:

            cursor.execute(
                '''
                INSERT INTO campaigns
                (
                    name,
                    call_type,
                    caller_id,
                    queue_name,
                    crm,
                    pause_codes,
                    dial_ratio,
                    wrap_time,
                    active
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',

                (
                    name,
                    call_type,
                    caller_id,
                    queue_name,
                    crm,
                    pause_codes,
                    dial_ratio,
                    wrap_time,
                    active
                )
            )

            conn.commit()

            return redirect(url_for('campaigns'))

        except sqlite3.IntegrityError:

            return "Campaign already exists"

    conn.close()

    return render_template('create_campaign.html')
@app.route('/assign_campaign', methods=['GET', 'POST'])
def assign_campaign():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        agent_id = request.form['agent_id']
        campaign_id = request.form['campaign_id']

        cursor.execute(
           '''
           SELECT * FROM agent_campaigns
           WHERE agent_id=? AND campaign_id=?
           ''',
           (agent_id, campaign_id)
        )

        existing = cursor.fetchone()

        if not existing:

            cursor.execute(
               '''
              INSERT INTO agent_campaigns (agent_id, campaign_id)
              VALUES (?, ?)
              ''',
              (agent_id, campaign_id)
            )

        conn.commit()

    
    cursor.execute('SELECT id, name FROM agents')
    agents = cursor.fetchall()

    cursor.execute('SELECT id, name FROM campaigns')
    campaigns = cursor.fetchall()

    cursor.execute('''
        SELECT agents.name, campaigns.name
        FROM agent_campaigns
        JOIN agents ON agent_campaigns.agent_id = agents.id
        JOIN campaigns ON agent_campaigns.campaign_id = campaigns.id
    ''')

    mappings = cursor.fetchall()

    conn.close()

    return render_template(
        'assign_campaign.html',
        agents=agents,
        campaigns=campaigns,
        mappings=mappings
    )
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect(url_for('login'))
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO
import random
import time
from threading import Thread

app = Flask(__name__)
app.secret_key = 'secret123'

socketio = SocketIO(app, async_mode='threading')

stats = {
    "agents": 11,
    "active_calls": 6,
    "waiting_calls": 2,
    "total_calls": 3102
}

USERNAME = "admin"
PASSWORD = "admin123"

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == USERNAME and password == PASSWORD:
            session['user'] = username
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html', stats=stats)

def update_stats():
    while True:
        stats['active_calls'] = random.randint(1, 15)
        stats['waiting_calls'] = random.randint(0, 10)
        stats['total_calls'] += random.randint(1, 5)

        socketio.emit('update', stats)

        time.sleep(5)

thread = Thread(target=update_stats)
thread.daemon = True
thread.start()
@app.route('/agents', methods=['GET', 'POST'])
def agents():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        extension = request.form['extension']
        password = request.form['password']
        status = request.form['status']

        try:
            cursor.execute(
                'INSERT INTO agents (name, extension, password, status) VALUES (?, ?, ?, ?)',
                (name, extension, password, status)
            )
            conn.commit()

            return redirect(url_for('agents'))

        except sqlite3.IntegrityError:
            return "Extension already exists"

    cursor.execute('SELECT * FROM agents')
    agents = cursor.fetchall()

    conn.close()

    return render_template('agents.html', agents=agents)
@app.route('/delete_agent/<int:id>')
def delete_agent(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM agents WHERE id=?',
        (id,)
    )

    conn.commit()

    conn.close()

    return redirect(url_for('agents'))
@app.route('/edit_agent/<int:id>', methods=['GET', 'POST'])
def edit_agent(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']
        extension = request.form['extension']
        password = request.form['password']
        status = request.form['status']

        cursor.execute('''
            UPDATE agents
            SET
                name=?,
                extension=?,
                password=?,
                status=?
            WHERE id=?
        ''', (
            name,
            extension,
            password,
            status,
            id
        ))

        conn.commit()

        conn.close()

        return redirect(url_for('agents'))

    cursor.execute(
        'SELECT * FROM agents WHERE id=?',
        (id,)
    )

    agent = cursor.fetchone()

    conn.close()

    return render_template(
        'edit_agent.html',
        agent=agent
    )
@app.route('/agent-login', methods=['GET', 'POST'])
def agent_login():

    if request.method == 'POST':

        extension = request.form['extension']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Check agent login

        cursor.execute(
            'SELECT * FROM agents WHERE extension=? AND password=?',
            (extension, password)
        )

        agent = cursor.fetchone()

        if agent:

            # Get assigned campaigns

            cursor.execute('''
                SELECT campaigns.name
                FROM agent_campaigns
                JOIN campaigns
                ON agent_campaigns.campaign_id = campaigns.id
                WHERE agent_campaigns.agent_id = ?
            ''', (agent[0],))

            campaigns = cursor.fetchall()

            conn.close()

            return render_template(
                'select_campaign.html',
                agent=agent,
                campaigns=campaigns
            )

        else:

            conn.close()

            return "Invalid Login"

    return render_template('agent_login.html')
@app.route('/start-agent-session', methods=['POST'])
def start_agent_session():

    session['agent'] = request.form['agent_name']
    session['campaign'] = request.form['campaign']

    return redirect(url_for('agent_dashboard'))
@app.route('/agent-dashboard', methods=['GET', 'POST'])
def agent_dashboard():

    if 'agent' not in session:
        return redirect(url_for('agent_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        customer_name = request.form['customer_name']
        phone_number = request.form['phone_number']
        campaign = request.form['campaign']
        call_status = request.form['call_status']
        disposition = request.form['disposition']
        notes = request.form['notes']
        callback_date = request.form['callback_date']

        cursor.execute('''
            INSERT INTO calls
            (customer_name, phone_number, campaign, call_status, disposition, notes, callback_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_name,
            phone_number,
            campaign,
            call_status,
            disposition,
            notes,
            callback_date
        ))

        conn.commit()

    cursor.execute("SELECT * FROM calls ORDER BY id DESC")
    calls = cursor.fetchall()

    conn.close()

    return render_template('agent_dashboard.html', calls=calls)

@app.route('/campaigns')
def campaigns():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM campaigns')

    campaigns = cursor.fetchall()

    conn.close()

    return render_template('campaigns.html', campaigns=campaigns)
@app.route('/create_campaign', methods=['GET', 'POST'])
def create_campaign():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        name = request.form['name']

        call_type = request.form['call_type']

        caller_id = request.form['caller_id']

        queue_name = request.form['queue_name']

        crm = request.form['crm']

        pause_codes = request.form['pause_codes']

        dial_ratio = request.form['dial_ratio']

        wrap_time = request.form['wrap_time']

        active = request.form['active']

        try:

            cursor.execute(
                '''
                INSERT INTO campaigns
                (
                    name,
                    call_type,
                    caller_id,
                    queue_name,
                    crm,
                    pause_codes,
                    dial_ratio,
                    wrap_time,
                    active
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',

                (
                    name,
                    call_type,
                    caller_id,
                    queue_name,
                    crm,
                    pause_codes,
                    dial_ratio,
                    wrap_time,
                    active
                )
            )

            conn.commit()

            return redirect(url_for('campaigns'))

        except sqlite3.IntegrityError:

            return "Campaign already exists"

    conn.close()

    return render_template('create_campaign.html')
@app.route('/assign_campaign', methods=['GET', 'POST'])
def assign_campaign():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        agent_id = request.form['agent_id']
        campaign_id = request.form['campaign_id']

        cursor.execute(
           '''
           SELECT * FROM agent_campaigns
           WHERE agent_id=? AND campaign_id=?
           ''',
           (agent_id, campaign_id)
        )

        existing = cursor.fetchone()

        if not existing:

            cursor.execute(
               '''
              INSERT INTO agent_campaigns (agent_id, campaign_id)
              VALUES (?, ?)
              ''',
              (agent_id, campaign_id)
            )

        conn.commit()

    
    cursor.execute('SELECT id, name FROM agents')
    agents = cursor.fetchall()

    cursor.execute('SELECT id, name FROM campaigns')
    campaigns = cursor.fetchall()

    cursor.execute('''
        SELECT agents.name, campaigns.name
        FROM agent_campaigns
        JOIN agents ON agent_campaigns.agent_id = agents.id
        JOIN campaigns ON agent_campaigns.campaign_id = campaigns.id
    ''')

    mappings = cursor.fetchall()

    conn.close()

    return render_template(
        'assign_campaign.html',
        agents=agents,
        campaigns=campaigns,
        mappings=mappings
    )
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect(url_for('login'))
@app.route('/agent_logout')
def agent_logout():

    session.pop('agent', None)
    session.pop('campaign', None)

    return redirect(url_for('agent_login'))
@app.route('/reports')
@app.route('/reports', methods=['GET', 'POST'])
def reports():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    query = "SELECT * FROM calls WHERE 1=1"

    params = []

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    campaign = request.args.get('campaign')

    if start_date:
        query += " AND date(callback_date) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(callback_date) <= date(?)"
        params.append(end_date)

    if campaign:
        query += " AND campaign = ?"
        params.append(campaign)

    query += " ORDER BY id DESC"

    cursor.execute(query, params)

    calls = cursor.fetchall()

    cursor.execute("SELECT DISTINCT campaign FROM calls")
    campaigns = cursor.fetchall()

    conn.close()

    return render_template('report.html',  calls=calls, campaigns=campaigns)
@app.route('/export-report')
def export_report():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')

    query = "SELECT * FROM calls WHERE 1=1"

    params = []

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    campaign = request.args.get('campaign')

    if start_date:
        query += " AND date(callback_date) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(callback_date) <= date(?)"
        params.append(end_date)

    if campaign:
        query += " AND campaign = ?"
        params.append(campaign)

    df = pd.read_sql_query(query, conn, params=params)

    conn.close()

    file_name = 'call_reports.xlsx'

    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)
if __name__ == '__main__':
    socketio.run(app, debug=True)