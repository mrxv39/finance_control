

import db as db_module


def _count_gastos(conn, user_id):
  cur = conn.cursor()
  cur.execute("SELECT COUNT(*) FROM gastos WHERE user_id = ?", (user_id,))
  return int(cur.fetchone()[0])


def test_get_gastos_ok(client, login):
  r = client.get("/api/gastos")
  assert r.status_code == 200
  data = r.get_json()
  assert isinstance(data, list)


def test_post_gasto_creates_row(client, login, user_id):
  conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
  before = _count_gastos(conn, user_id)

  payload = {
    "fecha": "2026-01-21",
    "importe": 12.34,
    "categoria": "Alimentación",
    "concepto": "Supermercado",
    "nota": "test",
  }
  r = client.post("/api/gastos", json=payload)
  assert r.status_code in (200, 201)

  after = _count_gastos(conn, user_id)
  assert after == before + 1


def test_post_gasto_rejects_missing_amount(client, login):
  payload = {"fecha": "2026-01-21", "categoria": "Otros", "concepto": "Varios"}
  r = client.post("/api/gastos", json=payload)
  assert r.status_code in (400, 422)
