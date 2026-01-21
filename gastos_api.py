from flask import Blueprint, request, jsonify, session
from auth import login_required
from db import db_exec, db_all, db_one

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _rows_to_dicts(rows):
    """Convierte sqlite3.Row (o dicts) a lista de dicts JSON-serializable."""
    out = []
    for r in rows or []:
        # sqlite3.Row soporta dict(r)
        try:
            out.append(dict(r))
        except Exception:
            out.append(r)
    return out


@api_bp.get("/gastos")
@login_required
def api_get_gastos():
    user_id = int(session.get("user_id"))

    rows = db_all(
        "SELECT id, fecha, concepto, categoria, importe "
        "FROM gastos WHERE user_id = ? "
        "ORDER BY fecha DESC, id DESC",
        (user_id,)
    )
    return jsonify(_rows_to_dicts(rows))


@api_bp.post("/gastos")
@login_required
def api_post_gastos():
    user_id = int(session.get("user_id"))

    data = request.get_json(silent=True) or {}
    fecha = (data.get("fecha") or "").strip()
    concepto = (data.get("concepto") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    importe = data.get("importe")

    if not fecha or not concepto or importe is None:
        return jsonify({"ok": False, "error": "Faltan campos: fecha, concepto, importe"}), 400

    try:
        importe = float(importe)
    except Exception:
        return jsonify({"ok": False, "error": "importe debe ser numérico"}), 400

    if not categoria:
        categoria = "Sin categoría"

    db_exec(
        "INSERT INTO gastos (user_id, fecha, concepto, categoria, importe) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, fecha, concepto, categoria, importe)
    )
    return jsonify({"ok": True})


@api_bp.get("/resumen")
@login_required
def api_get_resumen():
    """
    Soporta:
      GET /api/resumen
      GET /api/resumen?mes=YYYY-MM
    """
    user_id = int(session.get("user_id"))
    mes = (request.args.get("mes") or "").strip()

    params = [user_id]
    where_mes = ""

    # Si viene mes=YYYY-MM filtramos por prefijo (fecha tipo 'YYYY-MM-DD')
    if mes:
        where_mes = " AND substr(fecha, 1, 7) = ? "
        params.append(mes)

    por_categoria = db_all(
        "SELECT categoria, ROUND(SUM(importe), 2) AS total "
        "FROM gastos "
        "WHERE user_id = ? " + where_mes +
        "GROUP BY categoria "
        "ORDER BY total DESC",
        tuple(params)
    )

    total = db_one(
        "SELECT ROUND(COALESCE(SUM(importe), 0), 2) AS total "
        "FROM gastos "
        "WHERE user_id = ? " + where_mes,
        tuple(params)
    )

    return jsonify({
        "total": (total["total"] if total else 0),
        "por_categoria": _rows_to_dicts(por_categoria),
    })
