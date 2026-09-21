"""Purpose: Shared pytest fixtures for backend tests. Owner: Chris (backend)."""

import pytest

from app import create_app
from extensions import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    # The Limiter in extensions.py is one shared instance reused by every
    # app created in these tests (the standard Flask-Limiter factory
    # pattern), so its in-memory counters must be cleared before each test -
    # otherwise requests from earlier tests would count towards this test's
    # limit, since the Flask test client always uses the same fake IP.
    # Storage only exists once some app has called limiter.init_app(), which
    # game-logic/validator tests never do, so skip the reset until then.
    if getattr(limiter, "_storage", None) is not None:
        limiter.reset()
    yield


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()
