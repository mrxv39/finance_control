import io
import db as db_module


def _count_gastos(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM gastos WHERE user_id = ?", (user_id,))
    return int(cur.fetchone()[0])


def test_import_csv_requires_login(client):
    """Test that CSV import requires authentication"""
    csv_content = "date,description,amount\n2026-01-30,Test,100.00"
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 302  # Redirect to login


def test_import_csv_no_file(client, login):
    """Test that endpoint rejects request without file"""
    r = client.post("/api/import/csv", data={}, content_type='multipart/form-data')
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False
    assert "file" in data["error"].lower()


def test_import_csv_empty_filename(client, login):
    """Test that endpoint rejects empty filename"""
    data = {
        'file': (io.BytesIO(b""), '')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False


def test_import_csv_non_csv_file(client, login):
    """Test that endpoint rejects non-CSV files"""
    data = {
        'file': (io.BytesIO(b"not a csv"), 'test.txt')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 400
    data = r.get_json()
    assert data["ok"] is False
    assert "csv" in data["error"].lower()


def test_import_csv_valid_transactions(client, login, user_id):
    """Test successful import of valid CSV transactions"""
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    before = _count_gastos(conn, user_id)
    
    csv_content = """date,description,amount
2026-01-20,Supermercado Dia,-45.50
2026-01-21,Gasolina Shell,-60.00
2026-01-22,Salario,2500.00
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'transactions.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 3
    assert result["skipped"] == 0
    assert result["duplicates"] == 0
    
    after = _count_gastos(conn, user_id)
    assert after == before + 3


def test_import_csv_empty_file(client, login, user_id):
    """Test import of empty CSV file"""
    csv_content = "date,description,amount\n"
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'empty.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 0


def test_import_csv_with_invalid_rows(client, login, user_id):
    """Test that invalid rows are skipped"""
    csv_content = """date,description,amount
2026-01-20,Valid transaction,-45.50
invalid-date,Should be skipped,-30.00
2026-01-21,,50.00
2026-01-22,No amount,
2026-01-23,Another valid one,-15.25
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'mixed.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 2  # Only 2 valid transactions


def test_import_csv_duplicate_detection(client, login, user_id):
    """Test that duplicate transactions are detected"""
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    
    # First import
    csv_content = """date,description,amount
2026-01-20,Supermercado,-45.50
2026-01-21,Gasolina,-60.00
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'first.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    result = r.get_json()
    assert result["imported"] == 2
    
    before = _count_gastos(conn, user_id)
    
    # Second import with same data
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'duplicate.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    result = r.get_json()
    assert result["imported"] == 0
    assert result["duplicates"] == 2
    
    after = _count_gastos(conn, user_id)
    assert after == before  # No new rows added


def test_import_csv_alternative_column_names(client, login, user_id):
    """Test CSV with alternative column names (Spanish)"""
    csv_content = """fecha,concepto,importe
2026-01-20,Compra supermercado,-45.50
2026-01-21,Combustible,-60.00
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'spanish.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 2


def test_import_csv_different_date_formats(client, login, user_id):
    """Test CSV with different date formats"""
    csv_content = """date,description,amount
2026-01-20,Format ISO,-10.00
20/01/2026,Format DD/MM/YYYY,-20.00
20-01-2026,Format DD-MM-YYYY,-30.00
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'dates.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 3


def test_import_csv_with_category_suggestion(client, login, user_id):
    """Test that category suggestions are applied during import"""
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    
    # First, create a previous transaction to train the suggestion system
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gastos (user_id, fecha, categoria, concepto, nota, importe, created_at) "
        "VALUES (?, '2026-01-15', 'Alimentación', 'Supermercado', 'Compra en Mercadona productos varios', -50.00, datetime('now'))",
        (user_id,)
    )
    conn.commit()
    
    # Now import a transaction with similar text
    csv_content = """date,description,amount
2026-01-20,Mercadona productos,-45.50
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'with_suggestion.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 1
    
    # Verify that the imported transaction has the suggested category
    cur.execute(
        "SELECT categoria, concepto FROM gastos WHERE user_id = ? AND fecha = '2026-01-20'",
        (user_id,)
    )
    row = cur.fetchone()
    assert row is not None
    # Should have gotten the suggestion from the previous transaction
    assert row[0] == 'Alimentación'  # categoria
    assert row[1] == 'Supermercado'  # concepto


def test_import_csv_missing_columns(client, login, user_id):
    """Test CSV with missing required columns"""
    csv_content = """date,description
2026-01-20,Missing amount column
"""
    
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'missing.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 0
    assert "No valid transactions" in result.get("message", "")


def test_import_csv_with_utf8_bom(client, login, user_id):
    """Test CSV with UTF-8 BOM (common in Excel exports)"""
    # UTF-8 BOM
    bom = b'\xef\xbb\xbf'
    csv_content = bom + """date,description,amount
2026-01-20,Transaction with BOM,-45.50
""".encode('utf-8')
    
    data = {
        'file': (io.BytesIO(csv_content), 'with_bom.csv')
    }
    r = client.post("/api/import/csv", data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    
    result = r.get_json()
    assert result["ok"] is True
    assert result["imported"] == 1
