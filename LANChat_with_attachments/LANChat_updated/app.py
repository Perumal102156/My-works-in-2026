
import os
import sys
import hmac
import sqlite3
import getpass
import uuid
import mimetypes
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, abort, g, flash, send_from_directory
)
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat.db"
UPLOAD_DIR = BASE_DIR / "uploads"
MAX_FILE_SIZE = 30 * 1024 * 1024
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

secret_key = os.environ.get("FLASK_SECRET_KEY")
if not secret_key or len(secret_key) < 32:
    raise RuntimeError(
        "Set FLASK_SECRET_KEY to a persistent random secret of at least 32 characters."
    )

app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # This prototype uses HTTP on your LAN. Use HTTPS before production.
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=1800,
    # Allow one 30 MiB file plus a small multipart-form overhead.
    MAX_CONTENT_LENGTH=MAX_FILE_SIZE + (256 * 1024),
)

socketio = SocketIO(app, async_mode="threading")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                edited_at TEXT,
                FOREIGN KEY(sender_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS hidden_messages (
                user_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                hidden_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, message_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
        """)
        # Add attachment columns to existing databases without losing chat history.
        existing_columns = {row[1] for row in db.execute("PRAGMA table_info(messages)")}
        for column, declaration in (
            ("attachment_filename", "TEXT"),
            ("attachment_original_name", "TEXT"),
            ("attachment_mimetype", "TEXT"),
            ("attachment_size", "INTEGER"),
        ):
            if column not in existing_columns:
                db.execute(f"ALTER TABLE messages ADD COLUMN {column} {declaration}")
        db.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(id)")



def current_user():
    uid = session.get("uid")
    if not uid:
        return None

    return get_db().execute(
        "SELECT id, user_id, display_name, role, active "
        "FROM users WHERE id = ? AND active = 1",
        (uid,)
    ).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            session.clear()
            return redirect(url_for("login"))
        if user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def csrf_token():
    import secrets
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def valid_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(expected and submitted and hmac.compare_digest(submitted, expected))


@app.route("/", methods=["GET"])
def home():
    if current_user():
        return redirect(url_for("chat"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not valid_csrf():
            abort(400, "Invalid form token. Refresh the page and try again.")

        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        # Do not reveal whether the user ID exists.
        if user and user["active"] and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["uid"] = user["id"]
            session.permanent = True
            return redirect(url_for("chat"))

        flash("Invalid user ID or password, or account disabled.")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    if not valid_csrf():
        abort(400, "Invalid form token.")
    session.clear()
    return redirect(url_for("login"))


@app.route("/chat")
@login_required
def chat():
    user = current_user()
    return render_template("Chat.html", user=user)


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    db = get_db()

    if request.method == "POST":
        if not valid_csrf():
            abort(400, "Invalid form token.")

        action = request.form.get("action", "")

        if action == "create":
            user_id = request.form.get("user_id", "").strip()
            display_name = request.form.get("display_name", "").strip()
            password = request.form.get("password", "")
            role = request.form.get("role", "user")

            if (
                not user_id or len(user_id) > 50
                or not display_name or len(display_name) > 100
                or len(password) < 6
                or role not in ("admin", "user")
            ):
                flash("Check the fields. Passwords must be at least 12 characters.")
            else:
                try:
                    db.execute(
                        "INSERT INTO users "
                        "(user_id, display_name, password_hash, role) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            user_id, display_name,
                            generate_password_hash(password), role
                        )
                    )
                    db.commit()
                    flash("User account created.")
                except sqlite3.IntegrityError:
                    flash("That user ID already exists.")

        elif action == "toggle":
            try:
                target_id = int(request.form.get("target_id", ""))
            except ValueError:
                abort(400)

            target = db.execute(
                "SELECT id, role, active FROM users WHERE id = ?",
                (target_id,)
            ).fetchone()

            if target is None:
                abort(404)
            elif target["id"] == session["uid"]:
                flash("You cannot disable your own account.")
            elif target["role"] == "admin" and target["active"]:
                active_admins = db.execute(
                    "SELECT COUNT(*) FROM users "
                    "WHERE role = 'admin' AND active = 1"
                ).fetchone()[0]
                if active_admins <= 1:
                    flash("You cannot disable the last active administrator.")
                else:
                    db.execute(
                        "UPDATE users SET active = 0 WHERE id = ?",
                        (target_id,)
                    )
                    db.commit()
                    flash("Account disabled.")
            else:
                db.execute(
                    "UPDATE users SET active = ? WHERE id = ?",
                    (0 if target["active"] else 1, target_id)
                )
                db.commit()
                flash("Account status updated.")

        return redirect(url_for("admin"))

    users = db.execute(
        "SELECT id, user_id, display_name, role, active, created_at "
        "FROM users ORDER BY id"
    ).fetchall()

    return render_template("admin.html", users=users)


@app.route("/upload", methods=["POST"])
@login_required
def upload_attachment():
    if not valid_csrf():
        abort(400, "Invalid form token. Refresh the page and try again.")

    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        flash("Choose a file to attach.")
        return redirect(url_for("chat"))

    original_name = Path(uploaded.filename).name.strip()
    if not original_name:
        abort(400, "Invalid filename.")

    # Use a random server-side name; never use the supplied filename as a disk path.
    extension = Path(original_name).suffix[:20]
    stored_name = f"{uuid.uuid4().hex}{extension}"
    saved_path = UPLOAD_DIR / stored_name
    uploaded.save(saved_path)
    size = saved_path.stat().st_size
    if size == 0:
        saved_path.unlink(missing_ok=True)
        flash("The selected file is empty.")
        return redirect(url_for("chat"))
    if size > MAX_FILE_SIZE:
        saved_path.unlink(missing_ok=True)
        flash("File is too large. Maximum size is 30 MB per file.")
        return redirect(url_for("chat"))

    mimetype = uploaded.mimetype or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    # Only common raster images are rendered inline; other files download as attachments.
    if mimetype not in ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"):
        mimetype = "application/octet-stream" if mimetype == "image/svg+xml" else mimetype

    user = current_user()
    caption = request.form.get("message", "").strip()
    if len(caption) > 2000:
        saved_path.unlink(missing_ok=True)
        abort(400, "Caption is too long.")

    db = get_db()
    cursor = db.execute(
        """INSERT INTO messages
           (sender_id, message, attachment_filename, attachment_original_name,
            attachment_mimetype, attachment_size)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user["id"], caption, stored_name, original_name, mimetype, size)
    )
    db.commit()
    message_id = cursor.lastrowid
    payload = {
        "id": message_id, "sender_uid": user["id"],
        "user": user["display_name"], "user_id": user["user_id"],
        "message": caption, "created_at": "just now", "edited": False,
        "attachment_url": url_for("download_attachment", message_id=message_id),
        "attachment_name": original_name, "attachment_size": size,
        "attachment_is_image": mimetype in ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp")
    }
    socketio.emit("receive_message", payload)
    return redirect(url_for("chat"))


@app.route("/attachment/<int:message_id>")
@login_required
def download_attachment(message_id):
    user = current_user()
    row = get_db().execute("""
        SELECT m.attachment_filename, m.attachment_original_name,
               m.attachment_mimetype, m.attachment_size
        FROM messages AS m
        WHERE m.id = ? AND m.attachment_filename IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM hidden_messages AS h
              WHERE h.message_id = m.id AND h.user_id = ?
          )
    """, (message_id, user["id"])).fetchone()
    if row is None:
        abort(404)
    is_image = row["attachment_mimetype"] in ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp")
    response = send_from_directory(
        UPLOAD_DIR, row["attachment_filename"],
        as_attachment=not is_image,
        download_name=row["attachment_original_name"],
        mimetype=row["attachment_mimetype"]
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@socketio.on("connect")
def socket_connect(auth=None):
    user = current_user()
    if user is None:
        return False

    join_room(f"user_{user['id']}")
    rows = get_db().execute("""
        SELECT m.id, m.sender_id, u.display_name, u.user_id,
               m.message, m.created_at, m.edited_at,
               m.attachment_filename, m.attachment_original_name,
               m.attachment_mimetype, m.attachment_size
        FROM messages AS m
        JOIN users AS u ON u.id = m.sender_id
        WHERE NOT EXISTS (
            SELECT 1 FROM hidden_messages AS h
            WHERE h.message_id = m.id AND h.user_id = ?
        )
        ORDER BY m.id
    """, (user["id"],)).fetchall()

    emit("chat_history", [{
        "id": row["id"], "sender_uid": row["sender_id"],
        "user": row["display_name"], "user_id": row["user_id"],
        "message": row["message"], "created_at": row["created_at"],
        "edited": bool(row["edited_at"]),
        "attachment_url": url_for("download_attachment", message_id=row["id"]) if row["attachment_filename"] else None,
        "attachment_name": row["attachment_original_name"],
        "attachment_size": row["attachment_size"],
        "attachment_is_image": bool(row["attachment_mimetype"] in ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"))
    } for row in rows])


@socketio.on("send_message")
def send_message(data):
    user = current_user()
    if user is None:
        return False
    if not isinstance(data, dict):
        return

    message = data.get("message", "")
    if not isinstance(message, str):
        return
    message = message.strip()
    if not message:
        return
    if len(message) > 2000:
        emit("chat_error", {"message": "Message is too long."})
        return

    db = get_db()
    cursor = db.execute(
        "INSERT INTO messages (sender_id, message) VALUES (?, ?)",
        (user["id"], message)
    )
    db.commit()
    emit("receive_message", {
        "id": cursor.lastrowid, "sender_uid": user["id"],
        "user": user["display_name"], "user_id": user["user_id"],
        "message": message, "created_at": "just now", "edited": False,
        "attachment_url": None, "attachment_name": None,
        "attachment_size": None, "attachment_is_image": False
    }, broadcast=True)


@socketio.on("edit_message")
def edit_message(data):
    user = current_user()
    if user is None:
        return False
    if not isinstance(data, dict):
        return
    try:
        message_id = int(data.get("id"))
    except (TypeError, ValueError):
        emit("chat_error", {"message": "Invalid message."})
        return

    new_text = data.get("message", "")
    if not isinstance(new_text, str):
        return
    new_text = new_text.strip()
    if not new_text or len(new_text) > 2000:
        emit("chat_error", {"message": "Message must contain 1–2000 characters."})
        return

    db = get_db()
    row = db.execute(
        "SELECT id, sender_id FROM messages WHERE id = ?", (message_id,)
    ).fetchone()
    if row is None:
        emit("chat_error", {"message": "Message not found."})
        return
    if row["sender_id"] != user["id"] and user["role"] != "admin":
        emit("chat_error", {"message": "You can edit only your own messages."})
        return

    db.execute(
        "UPDATE messages SET message = ?, edited_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_text, message_id)
    )
    db.commit()
    emit("message_edited", {"id": message_id, "message": new_text}, broadcast=True)


@socketio.on("delete_message")
def delete_message(data):
    user = current_user()
    if user is None:
        return False
    if not isinstance(data, dict):
        return
    try:
        message_id = int(data.get("id"))
    except (TypeError, ValueError):
        emit("chat_error", {"message": "Invalid message."})
        return

    db = get_db()
    row = db.execute(
        "SELECT id, sender_id FROM messages WHERE id = ?", (message_id,)
    ).fetchone()
    if row is None:
        emit("chat_error", {"message": "Message not found."})
        return
    if row["sender_id"] != user["id"] and user["role"] != "admin":
        emit("chat_error", {"message": "You can hide only your own messages."})
        return

    db.execute(
        "INSERT OR IGNORE INTO hidden_messages (user_id, message_id) VALUES (?, ?)",
        (user["id"], message_id)
    )
    db.commit()
    emit("message_hidden", {"id": message_id}, room=f"user_{user['id']}")

def create_admin():
    init_db()
    print("Create the first administrator account.")
    user_id = input("Admin user ID: ").strip()
    display_name = input("Admin display name: ").strip()
    password = getpass.getpass("Admin password (minimum 12 characters): ")
    confirm = getpass.getpass("Confirm password: ")

    if not user_id or len(user_id) > 50 or not display_name or len(display_name) > 100:
        print("Invalid user ID or display name.")
        return

    if len(password) < 12 or password != confirm:
        print("Passwords must match and contain at least 12 characters.")
        return

    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO users "
                "(user_id, display_name, password_hash, role) "
                "VALUES (?, ?, ?, 'admin')",
                (user_id, display_name, generate_password_hash(password))
            )
        print("Administrator created successfully.")
    except sqlite3.IntegrityError:
        print("That user ID already exists.")


if __name__ == "__main__":
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        create_admin()
    else:
        socketio.run(app, host="0.0.0.0", port=5000, debug=False)
