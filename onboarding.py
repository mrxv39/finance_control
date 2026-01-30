# C:\Users\Usuario\Dropbox\app.gastos\onboarding.py

from db import get_db


def user_needs_onboarding(user_id: int) -> bool:
    """
    Devuelve True si el usuario debe ver el modal de onboarding.
    Regla: mostrar mientras users.has_imported_csv == 0 (o NULL / no existe).
    """
    db = get_db()
    row = db.execute(
        "SELECT has_imported_csv FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    # Si no existe el usuario (caso raro), por defecto no bloqueamos con onboarding
    if row is None:
        return False

    # sqlite3.Row -> acceso por clave
    try:
        has_imported = row["has_imported_csv"]
    except Exception:
        # fallback por si row_factory no es Row o viene como tupla
        has_imported = row[0] if row else 0

    # Interpretación segura: 1 => ya importó, 0/None => necesita onboarding
    return int(has_imported or 0) == 0
