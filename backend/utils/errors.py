"""Purpose: Custom API error type and JSON error handlers matching the
docs/api_contract.md error format {"error": {"code", "message"}}.
Owner: Chris (backend).
"""

from flask import jsonify


class ApiError(Exception):
    """Raised anywhere in the app to produce a contract-shaped JSON error."""

    def __init__(self, code, message, status_code=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _error_response(code, message, status_code):
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status_code
    return response


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return _error_response(error.code, error.message, error.status_code)

    @app.errorhandler(404)
    def handle_not_found(error):
        return _error_response(
            "not_found", "The requested resource was not found", 404
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return _error_response(
            "method_not_allowed",
            "This method is not allowed for this endpoint",
            405,
        )

    @app.errorhandler(429)
    def handle_rate_limited(error):
        return _error_response("rate_limited", "Too many requests", 429)

    @app.errorhandler(500)
    def handle_internal_error(error):
        return _error_response(
            "internal_error", "An unexpected error occurred", 500
        )
