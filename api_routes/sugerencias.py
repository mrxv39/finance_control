from flask import request, jsonify, session
from auth import login_required
from db import db_all
from api_routes.blueprint import api_bp
from api_routes.utils import escape_like


@api_bp.get("/sugerir")
@login_required
def api_sugerir():
    """
    Sugiere categoria + concepto a partir de la nota (modo "contiene"):
    - Busca en gastos anteriores del usuario donde nota LIKE %texto%
    - Devuelve combinaciones (categoria, concepto) más repetidas (top 5)
    - Incluye sugerencia principal (top 1)
    """
    user_id = int(session.get("user_id"))
    nota = (request.args.get("nota") or "").strip()

    if len(nota) < 3:
        return jsonify({"ok": True, "sugerencia": None, "matches": []})

    esc = escape_like(nota)
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


@api_bp.get("/sugerir_nota")
@login_required
def api_sugerir_nota():
    """
    Autocompletar de NOTAS por prefijo:
    - Cuando el usuario escribe 'l' debe sugerir notas guardadas que empiecen por 'l'
      (ej. 'late ron').
    - Devuelve top 8 notas distintas (más frecuentes y recientes).
    - También devuelve la categoria/concepto más reciente asociada a esa nota (para autopoblar).
    """
    user_id = int(session.get("user_id"))
    pref = (request.args.get("pref") or "").strip()

    if len(pref) < 1:
        return jsonify({"ok": True, "matches": []})

    esc = escape_like(pref)
    like = f"{esc}%"

    rows = db_all(
        """
        SELECT
          nota,
          MAX(id) AS last_id,
          COUNT(*) AS n
        FROM gastos
        WHERE user_id = ?
          AND COALESCE(nota,'') LIKE ? ESCAPE '\\'
          AND TRIM(COALESCE(nota,'')) <> ''
        GROUP BY nota
        ORDER BY n DESC, last_id DESC
        LIMIT 8
        """,
        (user_id, like)
    )

    matches = []
    for r in rows or []:
        nota_txt = r["nota"]
        # Para cada nota sugerida, sacamos la categoría/concepto del registro más reciente con esa nota
        meta = db_all(
            """
            SELECT categoria, COALESCE(concepto,'') AS concepto
            FROM gastos
            WHERE user_id = ? AND nota = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, nota_txt)
        )
        cat = meta[0]["categoria"] if meta else ""
        con = meta[0]["concepto"] if meta else ""

        matches.append({
            "nota": nota_txt,
            "n": r["n"],
            "categoria": cat,
            "concepto": con,
        })

    return jsonify({"ok": True, "matches": matches})
