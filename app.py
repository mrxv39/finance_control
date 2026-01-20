import os
from flask import Flask, render_template, redirect, url_for, session
from db import init_db, close_db
from schema import ensure_schema

from auth import auth_bp
from gastos_api import gastos_api
from static_routes import static_routes

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# PIN opcional
app.config["APP_PIN"] = os.environ.get("APP_PIN", "")

# DB en Fly
DB_PATH = os.environ.get("DB_PATH", "/data/gastos.db")
init_db(DB_PATH)
app.teardown_appcontext(close_db)

# crear tablas al arrancar
with app.app_context():
    ensure_schema()

# blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(gastos_api)
app.register_blueprint(static_routes)


@app.get("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    return render_template("index.html")


if __name__ == "__main__":
    # Local: si existe gastos.db al lado, úsalo
    if os.path.exists("gastos.db") and DB_PATH == "/data/gastos.db":
        init_db(os.path.abspath("gastos.db"))
        with app.app_context():
            ensure_schema()

    app.run(host="0.0.0.0", port=5000, debug=True)
