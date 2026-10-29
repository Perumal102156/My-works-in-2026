LAN Chat Application - Edit/Delete Update

Included:
- app.py: Flask-SocketIO backend with persistent chat messages, edit permissions, and per-user hide actions.
- templates/Chat.html: chat UI with Edit and Delete controls.
- templates/admin.html and templates/login.html: existing pages.
- chat.db: your existing database, preserved and extended with new tables on startup.

IMPORTANT BEFORE RUNNING
1. Stop the running LAN Chat server on the host computer.
2. Make a backup copy of your current LANChat folder, especially chat.db.
3. Extract this ZIP to a new test folder or copy the included app.py and templates/Chat.html into your existing project.
4. Keep your existing FLASK_SECRET_KEY environment variable configured (at least 32 characters). Do not generate a different key for every launch.
5. Run with the same Python environment/dependencies you already use:
   python app.py
   The app creates the messages and hidden_messages tables automatically.
6. Test with two accounts/browser sessions:
   - A user can edit/hide their own messages.
   - Admin can edit/hide any message.
   - Hiding a message only hides it for that account, including after reconnect/login.
   - Editing changes the shared message for everyone.

Notes:
- Message history is now stored in SQLite.
- Editing is shared and marked "(edited)".
- Delete means "hide from my view"; it does not erase the shared message.
- This ZIP intentionally excludes the bundled venv directory. Continue using your existing environment.
- This prototype uses HTTP on the LAN; use HTTPS before production deployment.
