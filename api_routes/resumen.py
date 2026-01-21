from flask import request, jsonify, session
from auth import login_required
from db import db_all, db_one
from api_routes.blueprint import api_bp
from api_routes.utils import rows_to_dicts


@api_bp.get("/resumen")
@login_required
def api_get_resumen():
    user_id = int(session.get("user_id"))
    mes = (request.args.get("mes") or "").strip()

    params = [user_id]
    where_mes = ""
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
        "por_categoria": rows_to_dicts(por_categoria),
    })
