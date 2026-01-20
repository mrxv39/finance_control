from db import db_exec, db_all


def ensure_schema():
    # -----------------------------
    # Tabla users
    # -----------------------------
    db_exec("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # -----------------------------
    # Tabla gastos (ajustada a tu API: usa columna 'nota')
    # -----------------------------
    db_exec("""
    CREATE TABLE IF NOT EXISTS gastos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      fecha TEXT NOT NULL DEFAULT (date('now')),
      categoria TEXT NOT NULL DEFAULT '',
      concepto TEXT NOT NULL DEFAULT '',
      importe REAL NOT NULL DEFAULT 0,
      nota TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # -----------------------------
    # Migraciones defensivas (por si la DB antigua no tuviera columnas)
    # -----------------------------
    try:
        cols = db_all("PRAGMA table_info(gastos)")
    except Exception:
        cols = []

    col_names = {c["name"] for c in cols} if cols else set()

    # Asegurar user_id
    if "user_id" not in col_names:
        try:
            db_exec("ALTER TABLE gastos ADD COLUMN user_id INTEGER")
        except Exception:
            pass

    # Asegurar 'nota' (tu API la usa)
    if "nota" not in col_names:
        try:
            db_exec("ALTER TABLE gastos ADD COLUMN nota TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass

    # Compatibilidad: si existía 'notas' (plural) pero no 'nota', copiar datos
    # (No borramos 'notas' porque SQLite no permite DROP COLUMN fácil; no molesta.)
    if ("notas" in col_names) and ("nota" in col_names):
        try:
            # Copiar solo donde nota esté vacía para no pisar datos nuevos
            db_exec("""
                UPDATE gastos
                SET nota = COALESCE(notas, '')
                WHERE (nota IS NULL OR nota = '')
            """)
        except Exception:
            pass

    # -----------------------------
    # Índices para rendimiento
    # -----------------------------
    try:
        db_exec("CREATE INDEX IF NOT EXISTS idx_gastos_user_id ON gastos(user_id)")
    except Exception:
        pass

    try:
        db_exec("CREATE INDEX IF NOT EXISTS idx_gastos_user_fecha ON gastos(user_id, fecha)")
    except Exception:
        pass

    try:
        db_exec("CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha)")
    except Exception:
        pass
