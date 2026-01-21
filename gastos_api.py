from flask import Blueprint, request, jsonify, session
from auth import login_required
from db import db_exec, db_all, db_one

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _rows_to_dicts(rows):
    out = []
    for r in rows or []:
        try:
            out.append(dict(r))
        except Exception:
            out.append(r)
    return out


def _escape_like(s: str) -> str:
    # Escapa % y _ para usar LIKE de forma segura
    return (s or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    return jsonify(_rows_to_dicts(rows))


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

    db_exec(
        "INSERT INTO gastos (user_id, fecha, categoria, concepto, nota, importe) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, fecha, categoria, concepto, nota, importe)
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
        "por_categoria": _rows_to_dicts(por_categoria),
    })


@api_bp.get("/sugerir")
@login_required
def api_sugerir():
    """
    Sugiere categoria + concepto a partir de la nota:
    - Busca en gastos anteriores del usuario donde nota LIKE %texto%
    - Devuelve la combinación (categoria, concepto) más repetida (con desempate por más reciente)
    """
    user_id = int(session.get("user_id"))
    nota = (request.args.get("nota") or "").strip()

    if len(nota) < 3:
        return jsonify({"ok": True, "sugerencia": None, "matches": []})

    esc = _escape_like(nota)
    like = f"%{esc}%"

    rows = db_all(
        """
        SELECT
          categoria,
          COALESCE(concepto,'') AS concepto,
          COUNT(*) AS n,
          MAX(id) AS last_id
        FROM gastos
        WHERE user_id = ?
          AND COALESCE(nota,'') LIKE ? ESCAPE '\\'
        GROUP BY categoria, COALESCE(concepto,'')
        ORDER BY n DESC, last_id DESC
        LIMIT 5
        """,
        (user_id, like)
    )

    matches = []
    for r in rows or []:
        matches.append({
            "categoria": r["categoria"],
            "concepto": r["concepto"],
            "n": r["n"],
        })

    sugerencia = None
    if matches:
        sugerencia = {
            "categoria": matches[0]["categoria"],
            "concepto": matches[0]["concepto"],
            "score": matches[0]["n"],
        }

    return jsonify({"ok": True, "sugerencia": sugerencia, "matches": matches})
