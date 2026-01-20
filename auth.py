from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, current_app
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from db import db_exec, db_one

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
    u = (request.form.get("username") or "").strip()
    p = (request.form.get("password") or "").strip()

    if len(u) < 3:
        flash("El usuario debe tener al menos 3 caracteres.")
        return redirect(url_for("auth.register"))
    if len(p) < 4:
        flash("La contraseña debe tener al menos 4 caracteres.")
        return redirect(url_for("auth.register"))

    if db_one("SELECT id FROM users WHERE username = ?", (u,)):
        flash("Ese usuario ya existe.")
        return redirect(url_for("auth.register"))

    db_exec(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (u, generate_password_hash(p))
    )
    flash("Usuario creado. Ahora inicia sesión.")
    return redirect(url_for("auth.login"))


@auth_bp.get("/login")
@require_pin
def login():
    return render_template("login.html")


@auth_bp.post("/login")
@require_pin
def login_post():
    u = (request.form.get("username") or "").strip()
    p = (request.form.get("password") or "").strip()

    user = db_one("SELECT id, username, password_hash FROM users WHERE username = ?", (u,))
    if not user or not check_password_hash(user["password_hash"], p):
        flash("Usuario o contraseña incorrectos.")
        return redirect(url_for("auth.login"))

    session["user_id"] = int(user["id"])
    session["username"] = user["username"]
    return redirect("/")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
