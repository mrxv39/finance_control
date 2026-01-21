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


def _get_or_create_categoria_id(nombre: str):
    nombre = (nombre or "").strip()
    if not nombre:
        nombre = "Otros"

    row = db_one("SELECT id FROM categorias WHERE nombre = ?", (nombre,))
    if row:
        return int(row["id"])

    db_exec("INSERT INTO categorias (nombre) VALUES (?)", (nombre,))
    row = db_one("SELECT id FROM categorias WHERE nombre = ?", (nombre,))
    return int(row["id"])


def _get_or_create_subcategoria_id(categoria_id: int, nombre: str):
    nombre = (nombre or "").strip()
    if not nombre:
        return None

    row = db_one(
        "SELECT id FROM subcategorias WHERE categoria_id = ? AND nombre = ?",
        (categoria_id, nombre)
    )
    if row:
        return int(row["id"])

    db_exec(
        "INSERT INTO subcategorias (categoria_id, nombre) VALUES (?, ?)",
        (categoria_id, nombre)
    )
    row = db_one(
        "SELECT id FROM subcategorias WHERE categoria_id = ? AND nombre = ?",
        (categoria_id, nombre)
    )
    return int(row["id"])


@api_bp.get("/gastos")
@login_required
def api_get_gastos():
    """
    GET /api/gastos?mes=YYYY-MM&categoria=...&q=...
    Devuelve: id, fecha, categoria (texto), nota, importe
    """
    user_id = int(session.get("user_id"))

    mes = (request.args.get("mes") or "").strip()          # YYYY-MM
    categoria_txt = (request.args.get("categoria") or "").strip()
    q = (request.args.get("q") or "").strip()

    # Intento 1: esquema nuevo (categoria_id/subcategoria_id + join)
    try:
        where = ["g.user_id = ?"]
        params = [user_id]

        if mes:
            where.append("substr(g.fecha, 1, 7) = ?")
            params.append(mes)

        if categoria_txt:
            where.append("c.nombre = ?")
            params.append(categoria_txt)

        if q:
            where.append("COALESCE(g.nota,'') LIKE ?")
            params.append(f"%{q}%")

        sql = (
            "SELECT g.id, g.fecha, "
            "COALESCE(c.nombre, 'Otros') AS categoria, "
            "COALESCE(g.nota, '') AS nota, "
            "g.importe "
            "FROM gastos g "
            "LEFT JOIN categorias c ON c.id = g.categoria_id "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY g.fecha DESC, g.id DESC"
        )

        rows = db_all(sql, tuple(params))
        return jsonify(_rows_to_dicts(rows))

    except Exception:
        # Fallback: esquema viejo (categoria texto / concepto, etc.)
        # Esto evita romper en local si aún no migraste.
        where = ["user_id = ?"]
        params = [user_id]

        if mes:
            where.append("substr(fecha, 1, 7) = ?")
            params.append(mes)

        if categoria_txt:
            where.append("categoria = ?")
            params.append(categoria_txt)

        if q:
            # en viejo puede llamarse nota o concepto; intentamos nota
            where.append("COALESCE(nota,'') LIKE ?")
            params.append(f"%{q}%")

        sql = (
            "SELECT id, fecha, categoria, COALESCE(nota,'') AS nota, importe "
            "FROM gastos "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY fecha DESC, id DESC"
        )

        rows = db_all(sql, tuple(params))
        return jsonify(_rows_to_dicts(rows))


@api_bp.post("/gastos")
@login_required
def api_post_gasto():
    """
    POST /api/gastos
    Body JSON (tu app.js):
      { importe, categoria, fecha, nota }
    Opcional (futuro):
      { subcategoria }
    """
    user_id = int(session.get("user_id"))

    data = request.get_json(silent=True) or {}
    fecha = (data.get("fecha") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    subcategoria = (data.get("subcategoria") or "").strip()
    nota = (data.get("nota") or "").strip()
    importe = data.get("importe")

    if not fecha or not categoria or importe is None:
        return jsonify({"ok": False, "error": "Faltan campos: fecha, categoria, importe"}), 400

    try:
        importe = float(importe)
    except Exception:
        return jsonify({"ok": False, "error": "importe debe ser numérico"}), 400

    # Esquema nuevo: guardar ids
    try:
        categoria_id = _get_or_create_categoria_id(categoria)
        subcategoria_id = _get_or_create_subcategoria_id(categoria_id, subcategoria)

        db_exec(
            "INSERT INTO gastos (user_id, fecha, categoria_id, subcategoria_id, nota, importe) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, fecha, categoria_id, subcategoria_id, nota, importe)
        )
        return jsonify({"ok": True})

    except Exception:
        # Fallback esquema viejo: guardar texto
        db_exec(
            "INSERT INTO gastos (user_id, fecha, categoria, nota, importe) VALUES (?, ?, ?, ?, ?)",
            (user_id, fecha, categoria, nota, importe)
        )
        return jsonify({"ok": True})


@api_bp.delete("/gastos/<int:gasto_id>")
@login_required
def api_delete_gasto(gasto_id: int):
    """
    DELETE /api/gastos/<id>
    """
    user_id = int(session.get("user_id"))

    # vale para esquema nuevo y viejo (ambos tienen id y user_id)
    db_exec("DELETE FROM gastos WHERE id = ? AND user_id = ?", (gasto_id, user_id))
    return jsonify({"ok": True})


@api_bp.get("/resumen")
@login_required
def api_get_resumen():
    """
    GET /api/resumen?mes=YYYY-MM
    Devuelve:
      { total: number, por_categoria: [{categoria,total}, ...] }
    """
    user_id = int(session.get("user_id"))
    mes = (request.args.get("mes") or "").strip()

    # Intento 1: esquema nuevo (join categorias)
    try:
        params = [user_id]
        where_mes = ""
        if mes:
            where_mes = " AND substr(g.fecha, 1, 7) = ? "
            params.append(mes)

        por_categoria = db_all(
            "SELECT COALESCE(c.nombre, 'Otros') AS categoria, "
            "ROUND(SUM(g.importe), 2) AS total "
            "FROM gastos g "
            "LEFT JOIN categorias c ON c.id = g.categoria_id "
            "WHERE g.user_id = ? " + where_mes +
            "GROUP BY COALESCE(c.nombre, 'Otros') "
            "ORDER BY total DESC",
            tuple(params)
        )

        total = db_one(
            "SELECT ROUND(COALESCE(SUM(g.importe), 0), 2) AS total "
            "FROM gastos g "
            "WHERE g.user_id = ? " + where_mes,
            tuple(params)
        )

        return jsonify({
            "total": (total["total"] if total else 0),
            "por_categoria": _rows_to_dicts(por_categoria),
        })

    except Exception:
        # Fallback esquema viejo (categoria texto)
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


# (Opcional) Endpoint para poblar dropdowns en el futuro:
@api_bp.get("/categorias")
@login_required
def api_get_categorias():
    """
    GET /api/categorias
    Devuelve:
      [{id, nombre, subcategorias:[{id,nombre}, ...]}, ...]
    """
    try:
        cats = db_all("SELECT id, nombre FROM categorias ORDER BY nombre", ())
        cats = _rows_to_dicts(cats)

        out = []
        for c in cats:
            subs = db_all(
                "SELECT id, nombre FROM subcategorias WHERE categoria_id = ? ORDER BY nombre",
                (c["id"],)
            )
            out.append({
                "id": c["id"],
                "nombre": c["nombre"],
                "subcategorias": _rows_to_dicts(subs)
            })

        return jsonify(out)
    except Exception:
        # Si aún no existen tablas en algún entorno
        return jsonify([])
