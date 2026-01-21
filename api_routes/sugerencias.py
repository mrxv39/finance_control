from flask import request, jsonify, session
from auth import login_required
from db import db_all
from api_routes.blueprint import api_bp
from api_routes.utils import escape_like


@api_bp.get("/sugerir")
@login_required
def api_sugerir():
    """
    Sugiere categoria + concepto a partir de la nota:
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
