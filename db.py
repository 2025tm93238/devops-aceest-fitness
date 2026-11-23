"""SQLite persistence helpers for ACEest Fitness & Gym.

Kept separate from the Flask routes so feature modules (blueprints) can share
the same per-request connection without circular imports.
"""

import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    target_weight REAL,
    target_adherence INTEGER
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT,
    adherence INTEGER
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT,
    workout_type TEXT,
    duration_min INTEGER,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT,
    weight REAL,
    waist REAL,
    bodyfat REAL
);
"""


def get_db():
    """Return a per-request SQLite connection, creating it on first use."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Columns added after v1.x. Applied with ALTER TABLE so a database created by an
# older release is upgraded in place (forward-compatible schema migration).
MIGRATIONS = {
    "clients": {
        "membership_status": "TEXT",
        "membership_end": "TEXT",
    },
}


def _apply_migrations(db):
    for table, columns in MIGRATIONS.items():
        existing = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
        for column, col_type in columns.items():
            if column in existing:
                continue
            try:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except sqlite3.OperationalError as exc:
                # Another worker added it between our check and the ALTER.
                if "duplicate column" not in str(exc):
                    raise


def init_db(app):
    """Create tables if they do not already exist and apply migrations."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        _apply_migrations(db)
        db.commit()


def client_row(name):
    """Fetch one client by name, or None."""
    return get_db().execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
