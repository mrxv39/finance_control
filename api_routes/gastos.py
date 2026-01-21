from flask import request, jsonify, session
from auth import login_required
from db import db_exec, db_all
from api_routes.blueprint import api_bp
from api_routes.utils import rows_to_dicts

from datetime import datetime, timezone


@api_bp.get("/gastos")
@login_required
def api_get_gastos():
    user_id = int(session.get("user_id"))

    mes = (request.args.get("mes") or "").strip()          # YYYY-MM
    categoria = (request.args.get("categoria") or "").strip()
    q = (request.args.get("q") or "").strip()

    where = ["user_id = ?"]
    params = [user_id]

    if mes:
        where.append("substr(fecha, 1, 7) = ?")
        params.append(mes)

    if categoria:
        where.append("categoria = ?")
        params.append(categoria)

    if q:
        where.append("COALESCE(nota,'') LIKE ?")
        params.append(f"%{q}%")

    sql = (
        "SELECT id, fecha, categoria, COALESCE(concepto,'') AS concepto, nota, importe "
        "FROM gastos "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY fecha DESC, id DESC"
    )

    rows = db_all(sql, tuple(params))
    return jsonify(rows_to_dicts(rows))


@api_bp.post("/gastos")
@login_required
def api_post_gasto():
    user_id = int(session.get("user_id"))

    data = request.get_json(silent=True) or {}
    fecha = (data.get("fecha") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    concepto = (data.get("concepto") or "").strip()
    nota = (data.get("nota") or "").strip()
    importe = data.get("importe")

    if not fecha or not categoria or importe is None:
        return jsonify({"ok": False, "error": "Faltan campos: fecha, categoria, importe"}), 400

    try:
        importe = float(importe)
    except Exception:
        return jsonify({"ok": False, "error": "importe debe ser numérico"}), 400

    created_at = datetime.now(timezone.utc).isoformat()

    db_exec(
        "INSERT INTO gastos (user_id, fecha, categoria, concepto, nota, importe, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, fecha, categoria, concepto, nota, importe, created_at)
    )
    return jsonify({"ok": True})


@api_bp.delete("/gastos/<int:gasto_id>")
@login_required
def api_delete_gasto(gasto_id: int):
    user_id = int(session.get("user_id"))

    db_exec(
        "DELETE FROM gastos WHERE id = ? AND user_id = ?",
        (gasto_id, user_id)
    )
    return jsonify({"ok": True})
