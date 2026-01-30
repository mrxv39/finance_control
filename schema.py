from db import db_exec, db_all


def ensure_schema():
    # -----------------------------
    # Tabla users (with email-based auth and confirmation)
    # -----------------------------
    db_exec("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT,
      email TEXT,
      password_hash TEXT NOT NULL,
      is_confirmed INTEGER NOT NULL DEFAULT 0,
      confirmation_token TEXT,
      confirmation_sent_at TEXT,
      has_imported_csv INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # -----------------------------
    # Tabla gastos
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
      source TEXT NOT NULL DEFAULT 'manual',
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # -----------------------------
    # Migraciones defensivas para users
    # -----------------------------
    try:
        user_cols = db_all("PRAGMA table_info(users)")
    except Exception:
        user_cols = []

    user_col_names = {c["name"] for c in user_cols} if user_cols else set()

    # Add email column if missing
    if "email" not in user_col_names:
        try:
            db_exec("ALTER TABLE users ADD COLUMN email TEXT")
        except Exception:
            pass

    # Add is_confirmed column if missing
    if "is_confirmed" not in user_col_names:
        try:
            db_exec("ALTER TABLE users ADD COLUMN is_confirmed INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

    # Add confirmation_token column if missing
    if "confirmation_token" not in user_col_names:
        try:
            db_exec("ALTER TABLE users ADD COLUMN confirmation_token TEXT")
        except Exception:
            pass

    # Add confirmation_sent_at column if missing
    if "confirmation_sent_at" not in user_col_names:
        try:
            db_exec("ALTER TABLE users ADD COLUMN confirmation_sent_at TEXT")
        except Exception:
            pass

    # Add has_imported_csv column if missing (for onboarding)
    if "has_imported_csv" not in user_col_names:
        try:
            db_exec("ALTER TABLE users ADD COLUMN has_imported_csv INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

    # Create unique index on email (ignore conflicts if already exists)
    try:
        db_exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    except Exception:
        pass

    # -----------------------------
    # Migraciones defensivas para gastos
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

    # Asegurar concepto (subcategoría)
    if "concepto" not in col_names:
        try:
            db_exec("ALTER TABLE gastos ADD COLUMN concepto TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass

    # Asegurar 'nota'
    if "nota" not in col_names:
        try:
            db_exec("ALTER TABLE gastos ADD COLUMN nota TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass

    # Asegurar 'source' (track CSV imports vs manual entry)
    if "source" not in col_names:
        try:
            db_exec("ALTER TABLE gastos ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'")
        except Exception:
            pass

    # Compatibilidad: si existía 'notas' (plural) pero no 'nota', copiar datos
    if ("notas" in col_names) and ("nota" in col_names):
        try:
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

    # Útil para sugerencias por nota (LIKE)
    try:
        db_exec("CREATE INDEX IF NOT EXISTS idx_gastos_user_nota ON gastos(user_id, nota)")
    except Exception:
        pass
