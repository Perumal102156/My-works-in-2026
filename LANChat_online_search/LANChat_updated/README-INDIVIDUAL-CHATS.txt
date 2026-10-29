LAN Chat - Individual / Private Conversations

NEW FEATURES
- General Chat remains available for shared messages.
- Start a private one-to-one chat by selecting a user in the left sidebar.
- Direct conversations are persisted and shared only with their two participants.
- Messages, edit events, and attachments are scoped to the selected conversation.
- Existing attachment support (up to 30 MB per file), image previews, edit, and hide-for-my-view are retained.
- Existing accounts are preserved. On startup, existing messages without a conversation ID are migrated into General Chat.

SAFE TESTING
1. Stop the old server and back up the complete project, chat.db, and uploads folder.
2. Extract this ZIP into a separate test folder.
3. Set the same persistent FLASK_SECRET_KEY (at least 32 characters) that you use for the existing app.
4. Use the Python environment where Flask and Flask-SocketIO are installed.
5. Run `python app.py` from the extracted project directory.
6. Log in with two different accounts in separate browsers. Choose each other under Start a chat and verify messages only appear in that private conversation.
7. Also test General Chat, attachment upload/download, editing, hiding, and reconnecting.

DATABASE AND STORAGE
- The app creates conversations and conversation_members tables and adds conversation_id to messages as needed.
- Old messages are assigned to General Chat (conversation ID 1).
- Keep chat.db and the uploads folder together. Back both up regularly.

SECURITY NOTES
- Server-side membership checks protect private conversations and attachment downloads.
- Admins can edit/hide messages only in conversations they can access as a participant; private conversations are not automatically exposed to admins.
- This is an internal LAN prototype. Use HTTPS and malware scanning before production use.

Online users and user search
----------------------------
The left-side user list now shows a green dot and "Online" for accounts with an
active Socket.IO connection; offline accounts remain searchable. Use the Search
users field to filter by display name, user ID, or role, then click a result to
open or reuse that private DM. Online presence is tracked in the running app
process, so it is intended for a single Flask-SocketIO server instance.
