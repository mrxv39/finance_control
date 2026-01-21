import os
import sys
import tempfile
import sqlite3
import pytest

# =========================
# AÑADIR RAÍZ DEL PROYECTO AL PYTHONPATH
# =========================
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import db as db_module  # noqa: E402
from app import create_app  # noqa: E402
from tests.helpers_db import mk_sqlite  # noqa: E402


@pytest.fixture()
def test_db_path():
    d = tempfile.mkdtemp(prefix="gastos_test_")
    return os.path.join(d, "test.db")


@pytest.fixture()
def app(test_db_path, monkeypatch):
    # 1) preparar sqlite aislada
    conn = mk_sqlite(test_db_path)

    # ✅ MUY IMPORTANTE: tu schema.py espera dict-like rows (c["name"])
    conn.row_factory = sqlite3.Row

    # 2) monkeypatch de acceso a DB
    def _get_db():
        return conn

    if hasattr(db_module, "get_db"):
        monkeypatch.setattr(db_module, "get_db", _get_db, raising=True)
    if hasattr(db_module, "get_conn"):
        monkeypatch.setattr(db_module, "get_conn", _get_db, raising=False)

    # 3) crear app Flask
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test-secret")

    yield app

    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture()
def client(app):
    return app.test_client()


def _insert_user(conn: sqlite3.Connection, username="u1", password_hash="x") -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, created_at) "
        "VALUES (?,?,datetime('now'))",
        (username, password_hash),
    )
    conn.commit()
    return int(cur.lastrowid)


@pytest.fixture()
def user_id():
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    return _insert_user(conn)


@pytest.fixture()
def login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
    return True
