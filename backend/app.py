"""Purpose: Flask application factory. Owner: Chris (backend).

Run from the backend/ directory so that plain imports (config, routes.*,
services.*, utils.*) resolve the same way for the Flask dev server and for
gunicorn:

    cd backend
    python app.py                                  # dev server
    gunicorn --workers 1 --threads 4 "app:create_app()"   # production-like
"""

import os

from flask import Flask, send_from_directory
from werkzeug.routing import BaseConverter

from config import Config
from extensions import limiter
from routes.game import game_bp
from routes.health import health_bp
from services.ai import create_ai_provider
from utils.errors import register_error_handlers

FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)


class FrontendPathConverter(BaseConverter):
    """Matches any path except one starting with "api/" (or exactly "api").

    Werkzeug dispatches a request to the first matching rule that also
    accepts its method, even if a more specific rule matches the same path
    with the wrong method - so a plain "/<path:path>" catch-all would steal
    GET requests to a POST-only /api/... route (returning the frontend
    fallback with 200 instead of a 405) and would swallow truly unknown
    /api/... paths as a 200 instead of a JSON 404. Excluding "api/" from
    this converter's regex means the frontend route can never match an API
    path at all, so Werkzeug's normal routing decides 404 vs 405 correctly.
    """

    regex = r"(?!api(?:/|$)).+"


def create_app(config_object=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)

    app.config["AI_PROVIDER"] = create_ai_provider(
        app.config["MOCK_AI"],
        region=app.config["BEDROCK_REGION"],
        model_id=app.config["BEDROCK_MODEL_ID"],
    )

    app.config["RATELIMIT_DEFAULT"] = app.config["RATE_LIMIT"]
    limiter.init_app(app)

    register_error_handlers(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(game_bp, url_prefix="/api")

    if os.path.isdir(FRONTEND_DIR):
        app.url_map.converters["frontend_path"] = FrontendPathConverter

        # Dev convenience: serve ../frontend at "/" so the whole app runs on
        # one origin, matching how Nginx will serve it in production.
        @app.route("/", defaults={"path": "index.html"})
        @app.route("/<frontend_path:path>")
        def serve_frontend(path):
            full_path = os.path.join(FRONTEND_DIR, path)
            if not os.path.isfile(full_path):
                path = "index.html"
            return send_from_directory(FRONTEND_DIR, path)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("FLASK_DEBUG", False))
