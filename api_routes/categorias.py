

from flask import request, jsonify, session
from auth import login_required
from db import db_all
from api_routes.blueprint import api_bp


# =========================
# CATEGORÍAS BASE DEL SISTEMA
# =========================
BASE_CATEGORIES = {
    "Vivienda": [
        "Alquiler / Hipoteca",
        "Comunidad",
        "IBI / Impuestos vivienda",
        "Electricidad",
        "Agua",
        "Gas",
        "Internet",
        "Teléfono",
        "Reparaciones",
        "Mantenimiento",
        "Muebles",
        "Electrodomésticos",
    ],
    "Alimentación": [
        "Supermercado",
        "Frutería",
        "Carnicería",
        "Panadería",
        "Bebidas",
        "Productos de limpieza",
        "Comida preparada",
    ],
    "Restaurantes y ocio": [
        "Restaurante",
        "Bar / Cafetería",
        "Comida rápida",
        "Delivery",
        "Copas",
        "Cine",
        "Espectáculos",
        "Suscripciones ocio",
    ],
    "Transporte": [
        "Combustible",
        "Transporte público",
        "Taxi / VTC",
        "Aparcamiento",
        "Peajes",
        "Mantenimiento vehículo",
        "Seguro coche",
        "Multas",
    ],
    "Salud": [
        "Médico",
        "Dentista",
        "Farmacia",
        "Seguro médico",
        "Gafas / Lentillas",
        "Terapias",
    ],
    "Ropa y calzado": [
        "Ropa",
        "Calzado",
        "Accesorios",
        "Arreglos",
    ],
    "Tecnología": [
        "Ordenador",
        "Móvil",
        "Tablet",
        "Accesorios",
        "Software / Apps",
        "Suscripciones digitales",
    ],
    "Educación": [
        "Cursos",
        "Libros",
        "Material escolar",
        "Formación online",
        "Idiomas",
    ],
    "Familia": [
        "Guardería",
        "Colegio",
        "Extraescolares",
        "Juguetes",
        "Material infantil",
    ],
    "Mascotas": [
        "Comida mascotas",
        "Veterinario",
        "Accesorios",
        "Seguro mascota",
    ],
    "Viajes": [
        "Transporte",
        "Alojamiento",
        "Comidas",
        "Actividades",
        "Seguro viaje",
    ],
    "Finanzas": [
        "Comisiones bancarias",
        "Intereses",
        "Préstamos",
        "Tarjetas",
        "Inversiones",
    ],
    "Regalos y donaciones": [
        "Regalos",
        "Donaciones",
        "Eventos",
    ],
    "Impuestos y tasas": [
        "IRPF",
        "Tasas municipales",
        "Otros impuestos",
    ],
    "Otros": [
        "Varios",
        "Imprevistos",
    ],
}


def _has_column(table: str, col: str) -> bool:
    rows = db_all(f"PRAGMA table_info({table})", ())
    for r in rows:
        name = r[1] if isinstance(r, (tuple, list)) else r["name"]
        if name == col:
            return True
    return False


@api_bp.get("/categorias")
@login_required
def api_get_categorias():
    """
    GET /api/categorias?q=texto

    Devuelve SOLO las categorías/subcategorías base del sistema.
    Incluye n = número de gastos del usuario que caen en esa pareja (cat, sub).

    Formato:
    [
      { "categoria": str, "subcategoria": str, "n": int }
    ]

    Nota: si la tabla no tiene 'subcategoria', usa 'concepto' como subcategoria.
    """
    user_id = int(session.get("user_id"))
    q = (request.args.get("q") or "").strip().lower()

    has_sub = _has_column("gastos", "subcategoria")
    has_con = _has_column("gastos", "concepto")

    if has_sub:
        sub_expr = "COALESCE(subcategoria,'')"
    elif has_con:
        sub_expr = "COALESCE(concepto,'')"
    else:
        sub_expr = "''"

    # 1) Conteo SOLO para parejas que existan en BASE_CATEGORIES
    #    (primero traemos lo usado por el usuario y luego filtramos por base)
    sql_used = (
        "SELECT COALESCE(categoria,'') AS categoria, "
        f"{sub_expr} AS subcategoria, "
        "COUNT(*) AS n "
        "FROM gastos "
        "WHERE user_id = ? "
        "GROUP BY COALESCE(categoria,''), "
        f"{sub_expr}"
    )
    rows = db_all(sql_used, (user_id,))

    used_counts = {}
    for r in rows:
        cat = (r[0] or "").strip()
        sub = (r[1] or "").strip()
        n = int(r[2] or 0)
        if not cat or not sub:
            continue
        used_counts[(cat, sub)] = n

    # 2) Emitir SOLO base + n (si existe) o 0
    out = []
    for cat, subs in BASE_CATEGORIES.items():
        for sub in subs:
            n = used_counts.get((cat, sub), 0)

            if q:
                haystack = f"{cat} {sub}".lower()
                if q not in haystack:
                    continue

            out.append({"categoria": cat, "subcategoria": sub, "n": n})

    # 3) Orden: más usadas arriba (pero siempre dentro de base)
    out.sort(key=lambda x: (-x["n"], x["categoria"], x["subcategoria"]))
    return jsonify(out)
