"""
Cyfernaut Discord Bot
Database layer - manages conversation memory using SQLite.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")


def init_db():
    """Create the messages and memories tables if they don't already exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                context_id  TEXT    NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('user', 'model')),
                content     TEXT    NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_context_time
            ON messages (context_id, timestamp)
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                context_id  TEXT    NOT NULL,
                fact        TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_context ON memories (context_id)")
        conn.commit()


def save_message(context_id: str, role: str, content: str):
    """Persist a single message turn to the database."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (context_id, role, content) VALUES (?, ?, ?)",
            (context_id, role, content),
        )
        conn.commit()


def get_history(context_id: str, limit: int = 15) -> list[dict]:
    """
    Retrieve the last `limit` messages for a given context.
    Returns a list formatted for the Gemini SDK's history parameter.
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, timestamp
                FROM messages
                WHERE context_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
            ORDER BY timestamp ASC
            """,
            (context_id, limit),
        ).fetchall()

    return [{"role": role, "parts": [{"text": content}]} for role, content in rows]


def save_fact(context_id: str, fact: str):
    """Save a long-term fact to the memories table."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO memories (context_id, fact) VALUES (?, ?)", (context_id, fact))
        conn.commit()


def get_memories(context_id: str) -> str:
    """Retrieve all stored facts for a context as a single formatted string."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT fact FROM memories WHERE context_id = ? ORDER BY created_at ASC",
            (context_id,)
        ).fetchall()
    
    if not rows:
        return "No specific memories yet."
    
    return "\n".join([f"- {row[0]}" for row in rows])


def clear_history(context_id: str):
    """Delete messages and memories for a given context."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE context_id = ?", (context_id,))
        conn.execute("DELETE FROM memories WHERE context_id = ?", (context_id,))
        conn.commit()
