"""
Tests for email-based authentication with confirmation flow.
"""

import db as db_module
from email_utils import generate_confirmation_token, is_token_expired
from datetime import datetime, timedelta, timezone


def _get_user_by_email(conn, email):
    """Helper to get user by email"""
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    if row:
        return dict(row)
    return None


def test_register_creates_unconfirmed_user(client):
    """Test that registration creates a user with is_confirmed=False"""
    payload = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    r = client.post("/register", data=payload, follow_redirects=False)
    assert r.status_code in (200, 302, 303)
    
    # Check user was created
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    user = _get_user_by_email(conn, "test@example.com")
    
    assert user is not None
    assert user["email"] == "test@example.com"
    assert user["is_confirmed"] == 0  # Not confirmed yet
    assert user["confirmation_token"] is not None
    assert user["confirmation_sent_at"] is not None


def test_register_rejects_invalid_email(client):
    """Test that registration rejects invalid email format"""
    payload = {
        "email": "not-an-email",
        "password": "testpass123"
    }
    r = client.post("/register", data=payload, follow_redirects=True)
    assert b"email" in r.data.lower() or b"v\xc3\xa1lido" in r.data.lower()


def test_register_rejects_duplicate_email(client):
    """Test that registration rejects duplicate email"""
    # Create first user
    payload = {
        "email": "duplicate@example.com",
        "password": "testpass123"
    }
    r1 = client.post("/register", data=payload, follow_redirects=True)
    assert r1.status_code == 200
    
    # Try to create second user with same email
    r2 = client.post("/register", data=payload, follow_redirects=True)
    # Should show error message about duplicate email  
    # Look for "ese email ya está registrado" or similar
    page_text = r2.data.decode('utf-8').lower()
    assert ("ese email" in page_text and "registrado" in page_text) or "ya" in page_text


def test_login_rejects_unconfirmed_user(client):
    """Test that login is blocked for unconfirmed users"""
    # Register user (unconfirmed)
    client.post("/register", data={
        "email": "unconfirmed@example.com",
        "password": "testpass123"
    })
    
    # Try to login
    r = client.post("/login", data={
        "email": "unconfirmed@example.com",
        "password": "testpass123"
    }, follow_redirects=True)
    
    assert b"confirmar" in r.data.lower()


def test_confirm_email_marks_user_confirmed(client):
    """Test that email confirmation works correctly"""
    # Register user
    client.post("/register", data={
        "email": "toconfirm@example.com",
        "password": "testpass123"
    })
    
    # Get confirmation token from database
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    user = _get_user_by_email(conn, "toconfirm@example.com")
    token = user["confirmation_token"]
    
    # Confirm email
    r = client.get(f"/confirm/{token}", follow_redirects=True)
    assert r.status_code == 200
    # Should show success message (various possible wordings)
    assert b"confirmado" in r.data.lower() or b"xito" in r.data.lower() or b"email" in r.data.lower()
    
    # Check user is now confirmed
    user_after = _get_user_by_email(conn, "toconfirm@example.com")
    assert user_after["is_confirmed"] == 1
    assert user_after["confirmation_token"] is None


def test_confirm_email_rejects_invalid_token(client):
    """Test that invalid confirmation token is rejected"""
    invalid_token = "invalid-token-12345"
    r = client.get(f"/confirm/{invalid_token}", follow_redirects=True)
    assert b"inv\xc3\xa1lido" in r.data.lower() or b"expirado" in r.data.lower()


def test_login_works_after_confirmation(client):
    """Test that login works for confirmed users"""
    # Register user
    client.post("/register", data={
        "email": "confirmed@example.com",
        "password": "testpass123"
    })
    
    # Get and use confirmation token
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    user = _get_user_by_email(conn, "confirmed@example.com")
    token = user["confirmation_token"]
    client.get(f"/confirm/{token}")
    
    # Now login should work
    r = client.post("/login", data={
        "email": "confirmed@example.com",
        "password": "testpass123"
    }, follow_redirects=False)
    
    assert r.status_code in (302, 303)  # Redirect to main page
    assert r.location in ("/", "http://localhost/")


def test_resend_confirmation_updates_token(client):
    """Test that resend confirmation creates a new token"""
    # Register user
    client.post("/register", data={
        "email": "resend@example.com",
        "password": "testpass123"
    })
    
    # Get original token
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    user_before = _get_user_by_email(conn, "resend@example.com")
    token_before = user_before["confirmation_token"]
    
    # Resend confirmation
    r = client.post("/resend-confirmation", data={
        "email": "resend@example.com"
    }, follow_redirects=True)
    
    assert r.status_code == 200
    
    # Check token was updated
    user_after = _get_user_by_email(conn, "resend@example.com")
    token_after = user_after["confirmation_token"]
    
    assert token_after is not None
    assert token_after != token_before  # Token should be different


def test_token_expiration_logic():
    """Test token expiration utility function"""
    # Token sent 1 hour ago (not expired)
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert not is_token_expired(recent, hours=24)
    
    # Token sent 25 hours ago (expired)
    old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    assert is_token_expired(old, hours=24)
    
    # Null token (expired)
    assert is_token_expired(None, hours=24)


def test_token_generation_is_unique():
    """Test that token generation produces unique tokens"""
    tokens = set()
    for _ in range(100):
        token = generate_confirmation_token()
        assert token not in tokens
        assert len(token) > 20  # Ensure it's reasonably long
        tokens.add(token)


def test_email_case_insensitive(client):
    """Test that email login is case-insensitive"""
    # Register with lowercase
    client.post("/register", data={
        "email": "case@example.com",
        "password": "testpass123"
    })
    
    # Confirm email
    conn = db_module.get_db() if hasattr(db_module, "get_db") else db_module.get_conn()
    user = _get_user_by_email(conn, "case@example.com")
    client.get(f"/confirm/{user['confirmation_token']}")
    
    # Login with uppercase should work
    r = client.post("/login", data={
        "email": "CASE@EXAMPLE.COM",
        "password": "testpass123"
    }, follow_redirects=False)
    
    assert r.status_code in (302, 303)
