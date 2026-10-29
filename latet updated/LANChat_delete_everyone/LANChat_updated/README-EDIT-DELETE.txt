LAN Chat Application - Edit/Delete update

This package is based on your uploaded LANChat project. It preserves the existing
users and passwords in chat.db and updates the chat backend and chat page.

FEATURES
- Messages are saved in SQLite and loaded when a user reconnects.
- Users can edit their own messages.
- Admins can edit any user's messages.
- Delete hides a message only for the logged-in account. Other users still see it.
- Hidden messages remain hidden for that account after reconnecting or logging in again.
- The server checks edit/delete permissions; the browser does not decide permissions.

INSTALL SAFELY
1. Stop the running chat server.
2. Make a backup of your current LANChat folder, especially chat.db.
3. Extract this ZIP to a separate test folder first.
4. Copy your existing FLASK_SECRET_KEY environment variable setting. It must be a
   persistent random secret with at least 32 characters. Do not change it on each run.
5. Use the same Python environment where Flask and Flask-SocketIO are installed.
6. In the extracted LANChat folder, run: python app.py
7. Open the chat from two browser sessions/accounts and test sending, editing, hiding,
   reconnecting, and logging in again.

DATABASE
On startup, the app creates the messages and hidden_messages tables if they do not
exist. The included chat.db preserves your existing Admin and EMP1 accounts. Keep a
backup before running and do not overwrite your original database until tested.

NOTE
Editing updates the shared message for everyone. Delete means "hide from my view";
it does not permanently erase the message from the shared database.

ATTACHMENTS (NEW)
- Users and administrators can attach one image or file to a chat message.
- Maximum upload size is 30 MiB (30 × 1024 × 1024 bytes) per file.
- Common raster images (JPEG, PNG, GIF, WebP, BMP) preview inside the chat.
  Other file types appear as download links.
- Files are stored in the LANChat/uploads folder; message metadata is stored in SQLite.
- Attachments are available only to signed-in users. If a user hides a message,
  that attachment is also hidden from that user's account. Hiding does not delete it
  for other users.
- Keep the uploads folder and chat.db together when backing up or moving the app.
- Only share files you trust. This LAN prototype does not scan uploaded files for malware.
