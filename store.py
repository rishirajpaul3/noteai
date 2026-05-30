import json
import os
import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "notetaker.db")))
_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            );
            CREATE TABLE IF NOT EXISTS calls (
                bot_id     TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL DEFAULT 0,
                data       TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            );
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER NOT NULL,
                key     TEXT NOT NULL,
                value   TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
            );
        """)
        _local.conn.commit()
    return _local.conn


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str) -> int:
    db = _conn()
    cur = db.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password_hash))
    db.commit()
    return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    row = _conn().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    row = _conn().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ── Calls (per user) ──────────────────────────────────────────────────────────

def save(bot_id: str, data: dict, user_id: int = 0) -> None:
    db = _conn()
    db.execute(
        "INSERT OR REPLACE INTO calls (bot_id, user_id, data) VALUES (?, ?, ?)",
        (bot_id, user_id, json.dumps(data)),
    )
    db.commit()


def get(bot_id: str) -> dict | None:
    row = _conn().execute("SELECT data FROM calls WHERE bot_id = ?", (bot_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def get_for_user(bot_id: str, user_id: int) -> dict | None:
    row = _conn().execute(
        "SELECT data FROM calls WHERE bot_id = ? AND user_id = ?", (bot_id, user_id)
    ).fetchone()
    return json.loads(row["data"]) if row else None


def all_calls(user_id: int | None = None) -> list[dict]:
    if user_id is not None:
        rows = _conn().execute(
            "SELECT data FROM calls WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    else:
        rows = _conn().execute("SELECT data FROM calls ORDER BY created_at DESC").fetchall()
    return [json.loads(r["data"]) for r in rows]


def update(bot_id: str, patch: dict) -> bool:
    row = _conn().execute("SELECT data FROM calls WHERE bot_id = ?", (bot_id,)).fetchone()
    if not row:
        return False
    data = json.loads(row["data"])
    data.update(patch)
    db = _conn()
    db.execute("UPDATE calls SET data = ? WHERE bot_id = ?", (json.dumps(data), bot_id))
    db.commit()
    return True


def remove(bot_id: str) -> None:
    db = _conn()
    db.execute("DELETE FROM calls WHERE bot_id = ?", (bot_id,))
    db.commit()


# ── Settings (per user) ───────────────────────────────────────────────────────

def get_setting(key: str, user_id: int = 0) -> str | None:
    row = _conn().execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key)
    ).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str, user_id: int = 0) -> None:
    db = _conn()
    db.execute(
        "INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)",
        (user_id, key, value),
    )
    db.commit()
