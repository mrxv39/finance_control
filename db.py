import os
import sqlite3
from pathlib import Path
from flask import g

# -----------------------------------------------------------------------------
# DB PATH strategy:
# - In Fly.io production: DB_PATH=/data/gastos.db
# - In local dev: fallback to ./data/gastos.db
# -----------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LOCAL_DB = BASE_DIR / "data" / "gastos.db"

DB_PATH = os.environ.get("DB_PATH") or str(DEFAULT_LOCAL_DB)


def _ensure_db_dir_exists(db_path: str) -> None:
    """
    Ensure the parent directory of the sqlite DB exists.
    """
    p = Path(db_path)
    parent = p.parent if p.parent else Path(".")
    parent.mkdir(parents=True, exist_ok=True)


def init_db(db_path=None):
    """
    Initializes the database file and directory.
    Compatible with calls like:
        init_db()
        init_db(DB_PATH)
    """
    path = db_path or DB_PATH
    _ensure_db_dir_exists(path)
    con = sqlite3.connect(path)
    con.close()


def get_db() -> sqlite3.Connection:
    """
    Returns a per-request SQLite connection stored in flask.g.
    """
    if "db" not in g:
        _ensure_db_dir_exists(DB_PATH)
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None) -> None:
    """
    Closes DB connection at the end of the request.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def db_exec(sql: str, params=()):
    """
    Execute INSERT / UPDATE / CREATE and commit.
    """
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur


def db_one(sql: str, params=()):
    """
    Fetch one row.
    """
    cur = get_db().execute(sql, params)
    row = cur.fetchone()
    cur.close()
    return row


def db_all(sql: str, params=()):
    """
    Fetch all rows.
    """
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows
