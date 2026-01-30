from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone
import re

from db import db_exec, db_one
from email_utils import (
    generate_confirmation_token,
    send_confirmation_email,
    is_token_expired
)

# IMPORTANTE: este nombre debe existir para que app.py lo importe
auth_bp = Blueprint("auth", __name__)


def require_pin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        pin = current_app.config.get("APP_PIN", "")
        if pin:
            if session.get("pin_ok"):
                return view(*args, **kwargs)
            return redirect(url_for("auth.pin"))
        return view(*args, **kwargs)
    return wrapped


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@auth_bp.get("/pin")
def pin():
    return render_template("pin.html")


@auth_bp.post("/pin")
def pin_post():
    pin_in = (request.form.get("pin") or "").strip()
    if pin_in == current_app.config.get("APP_PIN", ""):
        session["pin_ok"] = True
        return redirect(url_for("auth.login"))
    flash("PIN incorrecto")
    return redirect(url_for("auth.pin"))


@auth_bp.get("/register")
@require_pin
def register():
    return render_template("register.html")


@auth_bp.post("/register")
@require_pin
def register_post():
    """
    User registration with email and confirmation flow.
    Creates user with is_confirmed=False and sends confirmation email.
    """
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    # Validate email format
    if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        flash("Por favor ingresa un email válido.")
        return redirect(url_for("auth.register"))
    
    # Validate password length
    if len(password) < 4:
        flash("La contraseña debe tener al menos 4 caracteres.")
        return redirect(url_for("auth.register"))

    # Check if email already exists (normalize before checking)
    existing_user = db_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing_user:
        flash("Ese email ya está registrado.")
        return redirect(url_for("auth.register"))

    # Generate confirmation token
    token = generate_confirmation_token()
    sent_at = datetime.now(timezone.utc).isoformat()

    # Create user with is_confirmed=False
    try:
        db_exec(
            """INSERT INTO users (email, password_hash, is_confirmed, confirmation_token, confirmation_sent_at) 
               VALUES (?, ?, 0, ?, ?)""",
            (email, generate_password_hash(password), token, sent_at)
        )
    except Exception as e:
        # Handle unique constraint violation or other DB errors
        flash("Ese email ya está registrado.")
        return redirect(url_for("auth.register"))

    # Send confirmation email
    # Use request.host_url to get actual host/port instead of hardcoding
    confirmation_url = request.host_url.rstrip('/') + url_for("auth.confirm_email", token=token)
    email_sent = send_confirmation_email(email, confirmation_url)

    if email_sent:
        flash("Usuario creado. Revisa tu email para confirmar tu cuenta.", "success")
    else:
        flash("Usuario creado pero hubo un problema enviando el email de confirmación.", "warning")
    
    return redirect(url_for("auth.login"))


@auth_bp.get("/login")
@require_pin
def login():
    return render_template("login.html")


@auth_bp.post("/login")
@require_pin
def login_post():
    """
    User login with email.
    Only allows login if email is confirmed (is_confirmed=True).
    """
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()

    user = db_one("SELECT id, email, password_hash, is_confirmed FROM users WHERE email = ?", (email,))
    
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Email o contraseña incorrectos.")
        return redirect(url_for("auth.login"))

    # Check if email is confirmed
    if not user["is_confirmed"]:
        flash("Debes confirmar tu email antes de iniciar sesión. Revisa tu bandeja de entrada.")
        return redirect(url_for("auth.login"))

    session["user_id"] = int(user["id"])
    session["email"] = user["email"]
    return redirect("/")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.get("/confirm/<token>")
def confirm_email(token):
    """
    Email confirmation route.
    Validates the token, checks expiration, and marks user as confirmed.
    """
    if not token:
        flash("Token de confirmación inválido.")
        return redirect(url_for("auth.login"))
    
    # Find user with this token
    user = db_one(
        "SELECT id, email, confirmation_sent_at FROM users WHERE confirmation_token = ?",
        (token,)
    )
    
    if not user:
        flash("Token de confirmación inválido o expirado.")
        return redirect(url_for("auth.login"))
    
    # Check if token is expired (24 hours)
    if is_token_expired(user["confirmation_sent_at"], hours=24):
        flash("El token ha expirado. Por favor solicita un nuevo email de confirmación.")
        return redirect(url_for("auth.login"))
    
    # Mark user as confirmed and clear token
    db_exec(
        """UPDATE users 
           SET is_confirmed = 1, confirmation_token = NULL, confirmation_sent_at = NULL 
           WHERE id = ?""",
        (user["id"],)
    )
    
    flash("¡Email confirmado con éxito! Ahora puedes iniciar sesión.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/resend-confirmation")
@require_pin
def resend_confirmation():
    """
    Page to request a new confirmation email.
    """
    return render_template("resend_confirmation.html")


@auth_bp.post("/resend-confirmation")
@require_pin
def resend_confirmation_post():
    """
    Resend confirmation email to user.
    """
    email = (request.form.get("email") or "").strip().lower()
    
    if not email:
        flash("Por favor ingresa tu email.")
        return redirect(url_for("auth.resend_confirmation"))
    
    # Find user
    user = db_one(
        "SELECT id, email, is_confirmed FROM users WHERE email = ?",
        (email,)
    )
    
    if not user:
        # Don't reveal if email exists or not (security)
        flash("Si el email existe, recibirás un nuevo link de confirmación.")
        return redirect(url_for("auth.login"))
    
    if user["is_confirmed"]:
        flash("Tu cuenta ya está confirmada. Puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    
    # Generate new token
    token = generate_confirmation_token()
    sent_at = datetime.now(timezone.utc).isoformat()
    
    db_exec(
        """UPDATE users 
           SET confirmation_token = ?, confirmation_sent_at = ? 
           WHERE id = ?""",
        (token, sent_at, user["id"])
    )
    
    # Send confirmation email
    # Use request.host_url to get actual host/port instead of hardcoding
    confirmation_url = request.host_url.rstrip('/') + url_for("auth.confirm_email", token=token)
    send_confirmation_email(email, confirmation_url)
    
    flash("Si el email existe, recibirás un nuevo link de confirmación.", "success")
    return redirect(url_for("auth.login"))
