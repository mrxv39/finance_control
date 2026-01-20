from flask import Blueprint, send_from_directory

static_routes = Blueprint("static_routes", __name__)


@static_routes.route("/sw.js")
def sw():
    return send_from_directory("static", "sw.js")


@static_routes.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")
