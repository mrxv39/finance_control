from flask import Blueprint, request, jsonify, session
from db import db_exec, db_all
from auth import login_required

gastos_api = Blueprint("gastos_api", __name__)


@gastos_api.get("/api/gastos")
@login_required
def get_gastos():
    uid = session["user_id"]
    rows = db_all(
        """
        SELECT id, fecha, categoria, nota, importe, created_at
        FROM gastos
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (uid,)
    )
    return jsonify([dict(r) for r in rows])


@gastos_api.post("/api/gastos")
@login_required
def add_gasto():
    uid = session["user_id"]

    # Tu frontend manda JSON (POST /api/gastos)
    data = request.get_json(silent=True) or {}

    fecha = (data.get("fecha") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    nota = (data.get("nota") or "").strip()
    importe = data.get("importe", None)

    if not fecha or not categoria or importe is None:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    try:
        importe_val = float(importe)
    except Exception:
        return jsonify({"ok": False, "error": "Importe inválido"}), 400

    db_exec(
        """
        INSERT INTO gastos (fecha, categoria, importe, nota, created_at, user_id)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
        """,
        (fecha, categoria, importe_val, nota, uid)
    )
    return jsonify({"ok": True})


@gastos_api.post("/api/gastos/delete")
@login_required
def delete_gasto():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    gasto_id = data.get("id")

    try:
        gasto_id = int(gasto_id)
    except Exception:
        return jsonify({"ok": False, "error": "ID inválido"}), 400

    db_exec("DELETE FROM gastos WHERE id = ? AND user_id = ?", (gasto_id, uid))
    return jsonify({"ok": True})


@gastos_api.get("/api/resumen")
@login_required
def resumen():
    uid = session["user_id"]
    mes = (request.args.get("mes") or "").strip()  # esperado: "YYYY-MM"

    if not mes:
        return jsonify({"ok": False, "error": "Falta mes"}), 400

    # IMPORTANTE:
    # Tu fecha en DB está como "DD/MM/YYYY" (ej: 20/01/2026).
    # Para filtrar por mes "YYYY-MM" convertimos con substr:
    # yyyy-mm = substr(fecha,7,4) || '-' || substr(fecha,4,2)
    rows = db_all(
        """
        SELECT categoria, ROUND(SUM(importe), 2) AS total
        FROM gastos
        WHERE user_id = ?
          AND (substr(fecha,7,4) || '-' || substr(fecha,4,2)) = ?
        GROUP BY categoria
        ORDER BY total DESC
        """,
        (uid, mes)
    )

    total_mes_row = db_all(
        """
        SELECT ROUND(COALESCE(SUM(importe),0), 2) AS total_mes
        FROM gastos
        WHERE user_id = ?
          AND (substr(fecha,7,4) || '-' || substr(fecha,4,2)) = ?
        """,
        (uid, mes)
    )
    total_mes = float(total_mes_row[0]["total_mes"]) if total_mes_row else 0.0

    return jsonify({
        "ok": True,
        "mes": mes,
        "total_mes": total_mes,
        "por_categoria": [dict(r) for r in rows]
    })
