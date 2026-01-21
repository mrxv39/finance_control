from db import db_exec, db_one, db_all


def init_db():
    # ===== USERS =====
    db_exec("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)

    # ===== CATEGORIAS =====
    db_exec("""
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    )
    """)

    # ===== SUBCATEGORIAS =====
    db_exec("""
    CREATE TABLE IF NOT EXISTS subcategorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        UNIQUE (categoria_id, nombre),
        FOREIGN KEY (categoria_id) REFERENCES categorias(id)
    )
    """)

    # ===== GASTOS (base) =====
    # Si la tabla no existe, se creará con el esquema nuevo.
    db_exec("""
    CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        categoria_id INTEGER,
        subcategoria_id INTEGER,
        nota TEXT,
        importe REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (categoria_id) REFERENCES categorias(id),
        FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id)
    )
    """)

    # Seed inicial (solo si está vacío)
    seed_categorias()

    # Migraciones defensivas (si ya existía DB antigua)
    migrate_gastos_schema()
    migrate_gastos_data_to_ids()


def seed_categorias():
    existe = db_one("SELECT id FROM categorias LIMIT 1")
    if existe:
        return  # ya están cargadas

    categorias = {
        "Vivienda": [
            "Alquiler / Hipoteca", "Luz", "Agua", "Gas",
            "Internet", "Comunidad", "Mantenimiento", "Seguro hogar"
        ],
        "Alimentación": [
            "Supermercado", "Comida fuera", "Cafés / Bares", "Delivery"
        ],
        "Transporte": [
            "Gasolina", "Transporte público", "Taxi / VTC",
            "Parking", "Peajes", "Mantenimiento", "Seguro coche"
        ],
        "Gastos personales": [
            "Ropa", "Calzado", "Peluquería", "Higiene", "Suscripciones"
        ],
        "Salud": [
            "Farmacia", "Médico", "Dentista", "Gimnasio", "Seguro médico"
        ],
        "Ocio": [
            "Salidas", "Cine / Teatro", "Viajes", "Hobbies"
        ],
        "Tecnología": [
            "Móvil", "Ordenador", "Accesorios", "Software"
        ],
        "Finanzas": [
            "Comisiones", "Intereses", "Préstamos", "Ahorro"
        ],
        "Regalos y eventos": [
            "Regalos", "Cumpleaños", "Eventos"
        ],
        "Impuestos y tasas": [
            "IRPF", "Multas", "Tasas"
        ],
        "Mascotas": [
            "Comida", "Veterinario", "Accesorios"
        ],
        "Otros": [
            "Imprevistos", "Varios"
        ]
    }

    for cat, subs in categorias.items():
        db_exec("INSERT INTO categorias (nombre) VALUES (?)", (cat,))
        cat_id = db_one("SELECT id FROM categorias WHERE nombre = ?", (cat,))["id"]

        for sub in subs:
            db_exec(
                "INSERT INTO subcategorias (categoria_id, nombre) VALUES (?, ?)",
                (cat_id, sub)
            )


def _table_info_cols(table_name: str):
    # PRAGMA table_info devuelve: cid, name, type, notnull, dflt_value, pk
    rows = db_all(f"PRAGMA table_info({table_name})", ())
    return {r["name"] for r in rows}


def migrate_gastos_schema():
    """
    Si ya existía una tabla gastos antigua con columnas diferentes,
    añadimos columnas nuevas necesarias con ALTER TABLE (no destructivo).
    """
    cols = _table_info_cols("gastos")

    # En versiones antiguas podías tener categoria (texto) o concepto.
    # Aquí solo añadimos lo que falte del esquema nuevo.
    if "categoria_id" not in cols:
        db_exec("ALTER TABLE gastos ADD COLUMN categoria_id INTEGER", ())
    if "subcategoria_id" not in cols:
        db_exec("ALTER TABLE gastos ADD COLUMN subcategoria_id INTEGER", ())
    if "nota" not in cols:
        db_exec("ALTER TABLE gastos ADD COLUMN nota TEXT", ())

    # Nota: no eliminamos columnas antiguas (SQLite lo complica). No hace falta.


def migrate_gastos_data_to_ids():
    """
    Migra datos antiguos:
      - Si existe columna 'categoria' (texto) y gastos.categoria_id es NULL,
        intenta mapear por nombre a categorias.id
      - Si existe columna 'concepto' y nota está vacía, copia concepto -> nota
    """
    cols = _table_info_cols("gastos")

    # Copiar concepto -> nota si aplica
    if "concepto" in cols:
        db_exec(
            "UPDATE gastos SET nota = COALESCE(nota, concepto) "
            "WHERE (nota IS NULL OR nota = '') AND concepto IS NOT NULL AND concepto != ''",
            ()
        )

    # Mapear categoria texto -> categoria_id
    if "categoria" in cols:
        # Por cada categoria distinta en gastos, intenta crear/usar categoría en tabla categorias
        cats = db_all(
            "SELECT DISTINCT categoria FROM gastos WHERE categoria IS NOT NULL AND categoria != ''",
            ()
        )
        for r in cats:
            cat_txt = (r["categoria"] or "").strip()
            if not cat_txt:
                continue

            # Si no existe en categorias, la creamos (así no se pierde nada)
            row = db_one("SELECT id FROM categorias WHERE nombre = ?", (cat_txt,))
            if not row:
                db_exec("INSERT INTO categorias (nombre) VALUES (?)", (cat_txt,))
                row = db_one("SELECT id FROM categorias WHERE nombre = ?", (cat_txt,))

            cat_id = int(row["id"])

            # Asignar categoria_id solo donde esté NULL
            db_exec(
                "UPDATE gastos SET categoria_id = ? "
                "WHERE (categoria_id IS NULL OR categoria_id = 0) AND categoria = ?",
                (cat_id, cat_txt)
            )
