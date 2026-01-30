import csv
import io
from datetime import datetime, timezone
from flask import request, jsonify, session
from auth import login_required
from db import db_exec, db_all, get_db
from api_routes.blueprint import api_bp
from api_routes.utils import escape_like


def suggest_category_for_concept(user_id: int, concept: str):
    """
    Suggest category and subcategory based on concept text.
    Uses the same logic as /api/sugerir but simplified for import.
    Returns (categoria, concepto) or (None, None) if no match.
    """
    if not concept or len(concept.strip()) < 3:
        return None, None
    
    concept = concept.strip()
    esc = escape_like(concept)
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
        LIMIT 1
        """,
        (user_id, like)
    )
    
    if rows:
        return rows[0]["categoria"], rows[0]["concepto"]
    
    return None, None


def check_duplicate(user_id: int, fecha: str, concepto: str, importe: float) -> bool:
    """
    Check if a transaction already exists (same user, date, concept, and amount).
    Returns True if duplicate exists.
    Note: 'concepto' parameter is the description text stored in the 'nota' column.
    """
    rows = db_all(
        """
        SELECT id FROM gastos
        WHERE user_id = ?
          AND fecha = ?
          AND nota = ?
          AND importe = ?
        LIMIT 1
        """,
        (user_id, fecha, concepto, importe)
    )
    return len(rows) > 0


def parse_csv_file(file_content: str):
    """
    Parse CSV content and extract transactions.
    Expected columns: date, description/concept, amount
    Supports flexible column names (case-insensitive).
    
    Returns list of dicts: [{fecha, concepto, importe}, ...]
    """
    transactions = []
    reader = csv.DictReader(io.StringIO(file_content))
    
    if not reader.fieldnames:
        return transactions
    
    # Normalize column names (case-insensitive mapping)
    fieldnames_lower = {name.lower(): name for name in reader.fieldnames}
    
    # Try to find date column
    date_col = None
    for candidate in ['date', 'fecha', 'fecha_transaccion', 'transaction_date', 'datum']:
        if candidate in fieldnames_lower:
            date_col = fieldnames_lower[candidate]
            break
    
    # Try to find description/concept column
    desc_col = None
    for candidate in ['description', 'descripcion', 'concepto', 'concept', 'memo', 'nota']:
        if candidate in fieldnames_lower:
            desc_col = fieldnames_lower[candidate]
            break
    
    # Try to find amount column
    amount_col = None
    for candidate in ['amount', 'importe', 'monto', 'cantidad', 'value', 'valor']:
        if candidate in fieldnames_lower:
            amount_col = fieldnames_lower[candidate]
            break
    
    if not date_col or not desc_col or not amount_col:
        return transactions  # Missing required columns
    
    for row in reader:
        try:
            fecha_raw = (row.get(date_col) or "").strip()
            concepto_raw = (row.get(desc_col) or "").strip()
            importe_raw = (row.get(amount_col) or "").strip()
            
            if not fecha_raw or not concepto_raw or not importe_raw:
                continue  # Skip empty rows
            
            # Parse date (support multiple formats)
            fecha = parse_date(fecha_raw)
            if not fecha:
                continue  # Skip invalid dates
            
            # Parse amount (handle negative for expenses, positive for income)
            importe = float(importe_raw.replace(',', '.').replace(' ', ''))
            
            transactions.append({
                'fecha': fecha,
                'concepto': concepto_raw,
                'importe': importe
            })
        except (ValueError, TypeError):
            continue  # Skip invalid rows
    
    return transactions


def parse_date(date_str: str) -> str:
    """
    Parse date string and return YYYY-MM-DD format.
    Supports multiple date formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, etc.
    """
    date_str = date_str.strip()
    
    # Try common formats
    formats = [
        '%Y-%m-%d',      # 2026-01-30
        '%d/%m/%Y',      # 30/01/2026
        '%d-%m-%Y',      # 30-01-2026
        '%m/%d/%Y',      # 01/30/2026 (US format)
        '%Y/%m/%d',      # 2026/01/30
        '%d.%m.%Y',      # 30.01.2026
        '%Y%m%d',        # 20260130
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


@api_bp.post("/import/csv")
@login_required
def api_import_csv():
    """
    Import bank transactions from CSV file.
    
    Expected CSV format:
    - Columns: date, description, amount (flexible names)
    - One transaction per row
    - Negative amounts = expenses, positive = income
    
    Returns:
    {
      ok: true,
      imported: number,
      skipped: number,
      duplicates: number
    }
    """
    user_id = int(session.get("user_id"))
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"ok": False, "error": "No file selected"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"ok": False, "error": "File must be CSV"}), 400
    
    try:
        # Read and decode file content
        file_content = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM
        
        # Parse CSV
        transactions = parse_csv_file(file_content)
        
        if not transactions:
            return jsonify({
                "ok": True,
                "imported": 0,
                "skipped": 0,
                "duplicates": 0,
                "message": "No valid transactions found in CSV"
            })
        
        # Process transactions
        imported = 0
        skipped = 0
        duplicates = 0
        
        conn = get_db()
        created_at = datetime.now(timezone.utc).isoformat()
        
        for tx in transactions:
            fecha = tx['fecha']
            concepto = tx['concepto']
            importe = tx['importe']
            
            # Check for duplicates
            if check_duplicate(user_id, fecha, concepto, importe):
                duplicates += 1
                continue
            
            # Get category suggestion
            categoria, subconcepto = suggest_category_for_concept(user_id, concepto)
            
            # Use suggested category or default to empty
            if not categoria:
                categoria = ''
                subconcepto = ''
            
            try:
                # Insert transaction with source='csv_import' to track CSV imports
                db_exec(
                    "INSERT INTO gastos (user_id, fecha, categoria, concepto, nota, importe, source, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'csv_import', ?)",
                    (user_id, fecha, categoria, subconcepto, concepto, importe, created_at)
                )
                imported += 1
            except Exception:
                skipped += 1
                continue
        
        # Mark user as having imported CSV (for onboarding)
        if imported > 0:
            try:
                db_exec(
                    "UPDATE users SET has_imported_csv = 1 WHERE id = ?",
                    (user_id,)
                )
            except Exception:
                pass  # Don't fail import if flag update fails
        
        return jsonify({
            "ok": True,
            "imported": imported,
            "skipped": skipped,
            "duplicates": duplicates
        })
    
    except UnicodeDecodeError:
        return jsonify({"ok": False, "error": "File encoding not supported. Use UTF-8."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": f"Import failed: {str(e)}"}), 500
