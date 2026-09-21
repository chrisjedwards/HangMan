"""Purpose: Shared Flask extension instances. Owner: Chris (backend).

One Limiter instance is created here (the standard Flask-Limiter factory
pattern) and attached to each app via limiter.init_app(app) in
app.create_app(), configured from RATE_LIMIT (see config.py).
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
