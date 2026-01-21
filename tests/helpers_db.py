import os
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE,
  password_hash TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS gastos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  fecha TEXT,
  importe REAL,
  categoria TEXT,
  concepto TEXT,
  nota TEXT,
  created_at TEXT
);
"""


def mk_sqlite(db_path: str) -> sqlite3.Connection:
  os.makedirs(os.path.dirname(db_path), exist_ok=True)
  conn = sqlite3.connect(db_path)
  conn.execute("PRAGMA foreign_keys=ON;")
  conn.executescript(SCHEMA_SQL)
  conn.commit()
  return conn
