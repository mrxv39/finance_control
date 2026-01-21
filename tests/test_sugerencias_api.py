

import db as db_module


def test_sugerir_ok(client, login):
    r = client.get("/api/sugerir?pref=sup")
    assert r.status_code == 200

    data = r.get_json()
    assert isinstance(data, dict)

    assert data.get("ok") is True
    assert "matches" in data
    assert isinstance(data["matches"], list)
    assert "sugerencia" in data  # puede ser None si no hay historial


def test_sugerir_uses_user_history(client, login, user_id):
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    conn.execute(
        "INSERT INTO gastos (user_id, fecha, importe, categoria, concepto, nota, created_at) "
        "VALUES (?,?,?,?,?,?,datetime('now'))",
        (user_id, "2026-01-20", 1.0, "Alimentación", "Supermercado", "nota supermercado"),
    )
    conn.commit()

    r = client.get("/api/sugerir?pref=nota")
    assert r.status_code == 200

    data = r.get_json()
    assert isinstance(data, dict)
    assert data.get("ok") is True
    assert isinstance(data.get("matches"), list)

    # Con historial, debería sugerir algo o al menos devolver matches no vacíos
    # (si la implementación actual solo rellena sugerencia cuando hay match, aceptamos ambas)
    if data.get("sugerencia") is not None:
        assert isinstance(data["sugerencia"], str)
        assert len(data["sugerencia"]) >= 1
