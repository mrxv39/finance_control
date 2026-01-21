def rows_to_dicts(rows):
    out = []
    for r in rows or []:
        try:
            out.append(dict(r))
        except Exception:
            out.append(r)
    return out


def escape_like(s: str) -> str:
    # Escapa % y _ para usar LIKE de forma segura (también escapa \)
    return (s or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
