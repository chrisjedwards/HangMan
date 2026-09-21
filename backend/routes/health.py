"""Purpose: Health check endpoint. Owner: Chris (backend)."""

from flask import Blueprint, jsonify

from extensions import limiter

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
@limiter.exempt
def health():
    return jsonify({"status": "ok"})
