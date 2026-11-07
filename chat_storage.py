
import sqlite3
import os
from datetime import datetime

# Database location: same folder as this file
DB_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chat_history.db"
)


def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (conversation_id)
            REFERENCES conversations(id)
        )
    """)

    conn.commit()
    conn.close()


def create_conversation(title="New Chat"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO conversations (title, created_at) VALUES (?, ?)",
        (title, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return conversation_id


def save_message(conversation_id, role, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages
        (conversation_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        conversation_id,
        role,
        content,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_conversations():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, created_at
        FROM conversations
        ORDER BY id DESC
    """)

    result = cursor.fetchall()
    conn.close()
    return result


def get_messages(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id ASC
    """, (conversation_id,))

    result = cursor.fetchall()
    conn.close()
    return result


def delete_conversation(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM messages WHERE conversation_id = ?",
        (conversation_id,)
    )

    cursor.execute(
        "DELETE FROM conversations WHERE id = ?",
        (conversation_id,)
    )

    conn.commit()
    conn.close()


# Create database and tables automatically
initialize_database()

print("Chat storage system initialized successfully!")
