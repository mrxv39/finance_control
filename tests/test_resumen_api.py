

import db as db_module


def test_resumen_ok(client, login):
  r = client.get("/api/resumen")
  assert r.status_code == 200
  data = r.get_json()
  assert isinstance(data, dict)


def test_resumen_reflects_inserted_rows(client, login, user_id):
  conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
  conn.execute(
    "INSERT INTO gastos (user_id, fecha, importe, categoria, concepto, nota, created_at) "
    "VALUES (?,?,?,?,?,?,datetime('now'))",
    (user_id, "2026-01-21", 10.0, "Alimentación", "Supermercado", "x"),
  )
  conn.commit()

  r = client.get("/api/resumen")
  assert r.status_code == 200
  data = r.get_json()
  assert isinstance(data, dict)
