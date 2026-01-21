from flask import Blueprint, current_app, send_from_directory

static_bp = Blueprint("static_routes", __name__)


@static_bp.get("/sw.js")
def service_worker():
    return send_from_directory(current_app.static_folder, "sw.js")


@static_bp.get("/manifest.json")
def manifest():
    return send_from_directory(current_app.static_folder, "manifest.json")


@static_bp.get("/favicon.ico")
def favicon():
    # Opción A: si tienes static/favicon.ico
    return send_from_directory(current_app.static_folder, "favicon.ico")
