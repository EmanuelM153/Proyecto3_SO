import sqlite3
import threading

DB_NAME = "storage_service.db"

user_cache = {}
message_cache = {}
lock = threading.Lock()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                message TEXT NOT NULL,
                is_delivered BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_user(username, password_hash):
    with lock:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, password_hash)
                )
                user_cache[username] = {
                    "password_hash": password_hash,
                }
            except sqlite3.IntegrityError:
                raise ValueError("El usuario ya existe.")

def get_user(username):
    with lock:
        if username in user_cache:
            return user_cache[username]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username, password_hash, FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                user_cache[username] = {"password_hash": user[1]}
                return user_cache[username]
            return None

def save_message(sender, receiver, message):
    with lock:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (sender, receiver, message) VALUES (?, ?, ?)",
                (sender, receiver, message)
            )
            if receiver not in message_cache:
                message_cache[receiver] = []
            message_cache[receiver].append(message)

def get_messages(receiver):
    with lock:
        if receiver in message_cache:
            return message_cache[receiver]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, message FROM messages WHERE receiver = ? AND is_delivered = 0",
                (receiver,)
            )
            messages = cursor.fetchall()
            message_ids = [msg[0] for msg in messages]
            cursor.executemany(
                "UPDATE messages SET is_delivered = 1 WHERE id = ?", [(mid,) for mid in message_ids]
            )
            conn.commit()
            return [msg[1] for msg in messages]

def get_all_users():
    with lock:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users")
            users = [row[0] for row in cursor.fetchall()]
            return users

def get_conversation_history(user1, user2):
    with lock:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sender, message, timestamp
                FROM messages
                WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                ORDER BY timestamp ASC
            """, (user1, user2, user2, user1))
            messages = cursor.fetchall()
            return [{'sender': msg[0], 'message': msg[1], 'timestamp': msg[2]} for msg in messages]
