import pandas as pd
from flask import send_file
from flask import Flask, render_template, request, redirect
import random
import pymysql

app = Flask(__name__)

def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="ticketing_db",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit_ticket():

    name = request.form["name"]
    designation = request.form["designation"]
    issue = request.form["issue"]
    description = request.form["description"]

    ticket_id = "TKT" + str(random.randint(1000, 9999))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (ticket_id, name, designation, issue, description, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (ticket_id, name, designation, issue, description, "Open"))

    conn.commit()
    conn.close()

    return f"""
    <h2>Ticket Raised Successfully</h2>
    <p>Ticket ID: {ticket_id}</p>
    <a href="/">Back</a>
    """

@app.route("/engineer")
def engineer():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM tickets")
    tickets = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS count FROM tickets WHERE status='Open'")
    open_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM tickets WHERE status='Pending'")
    pending_count = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM tickets WHERE status='Closed'")
    closed_count = cursor.fetchone()["count"]

    conn.close()

    return render_template(
        "engineer.html",
        tickets=tickets,
        open_count=open_count,
        pending_count=pending_count,
        closed_count=closed_count
    )

@app.route("/update_ticket/<int:id>", methods=["POST"])
def update_ticket(id):

    status = request.form["status"]
    notes = request.form["notes"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tickets
        SET status=%s, resolution_notes=%s
        WHERE id=%s
    """, (status, notes, id))

    conn.commit()
    conn.close()

    return redirect("/engineer")
@app.route("/reports")
def reports():
    return render_template("reports.html")
@app.route("/download_report")
def download_report():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ticket_id,
            name,
            designation,
            issue,
            description,
            status,
            resolution_notes,
            created_at
        FROM tickets
    """)

    rows = cursor.fetchall()
    conn.close()

    print("REPORT ROWS:", rows)

    df = pd.DataFrame(rows)

    file_name = "mysql_ticket_report.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)