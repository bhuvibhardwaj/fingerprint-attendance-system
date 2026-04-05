import sqlite3
from contextlib import contextmanager
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    fingerprint_template TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def init_db(database_path):
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()


@contextmanager
def get_connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def insert_user(database_path, user_id, name, fingerprint_template):
    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users (id, name, fingerprint_template, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, fingerprint_template, datetime.utcnow().isoformat()),
        )


def fetch_user(database_path, user_id):
    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT id, name, fingerprint_template, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def fetch_users(database_path):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, created_at FROM users ORDER BY name ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_all_templates(database_path):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            "SELECT id, name, fingerprint_template FROM users ORDER BY name ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def insert_attendance(database_path, user_id, timestamp):
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO attendance (user_id, timestamp)
            VALUES (?, ?)
            """,
            (user_id, timestamp),
        )
        return cursor.lastrowid


def fetch_attendance(database_path):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT attendance.id, attendance.user_id, users.name, attendance.timestamp
            FROM attendance
            INNER JOIN users ON users.id = attendance.user_id
            ORDER BY attendance.timestamp DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_attendance_summary(database_path):
    with get_connection(database_path) as connection:
        total_users = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        total_attendance = connection.execute(
            "SELECT COUNT(*) AS count FROM attendance"
        ).fetchone()["count"]
        today_attendance = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM attendance
            WHERE date(timestamp) = date('now', 'localtime')
            """
        ).fetchone()["count"]
        return {
            "total_users": total_users,
            "total_attendance": total_attendance,
            "today_attendance": today_attendance,
        }


def delete_user(database_path, user_id):
    with get_connection(database_path) as connection:
        user = connection.execute(
            "SELECT id, name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            return None

        connection.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return dict(user)
