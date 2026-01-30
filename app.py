import os
from flask import Flask, redirect, url_for, session, render_template

import schema
from auth import auth_bp
from gastos_api import api_bp
from static_routes import static_bp



def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Secrets (Fly) / fallback local
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")
    app.config["APP_PIN"] = os.environ.get("APP_PIN", "")

    # DB schema init
    with app.app_context():
        # intenta funciones típicas; ajusta si tu schema usa otro nombre
        if hasattr(schema, "init_db"):
            schema.init_db()
        elif hasattr(schema, "ensure_schema"):
            schema.ensure_schema()
        elif hasattr(schema, "init_schema"):
            schema.init_schema()
        else:
            raise RuntimeError(
                "schema.py no expone init_db / ensure_schema / init_schema. "
                "Pega schema.py y lo ajusto."
            )

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(static_bp)

    @app.get("/")
    def root():
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        
        # Check if user needs onboarding (first CSV import)
        from onboarding import user_needs_onboarding
        user_id = session.get("user_id")
        needs_onboarding = user_needs_onboarding(user_id)
        
        return render_template("index.html", needs_onboarding=needs_onboarding)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
