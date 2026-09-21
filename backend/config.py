"""Purpose: Application configuration loaded from environment variables.
Owner: Chris (backend).
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int_env(name, default):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


class Config:
    # Game state (services/game_state.py) lives in a single process's memory.
    # Gunicorn MUST run with exactly one worker (--workers 1 --threads 4) in
    # production. With more than one worker, a game_id created on one worker
    # would be missing on another and lookups would wrongly return
    # game_not_found. See docs/implementation.md for the full design note.
    MOCK_AI = _bool_env("MOCK_AI", True)
    BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "eu-north-1")
    BEDROCK_MODEL_ID = os.environ.get(
        "BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    MAX_HINTS = _int_env("MAX_HINTS", 2)
    MAX_LIVES = _int_env("MAX_LIVES", 6)
    RATE_LIMIT = os.environ.get("RATE_LIMIT", "60 per minute")
    FLASK_DEBUG = _bool_env("FLASK_DEBUG", False)

    # Guards on real Bedrock calls (services/ai.py:BedrockAI). Not in
    # .env.example - these are advanced tuning knobs with safe defaults, and
    # .env.example/README.md are outside this task's scope (backend/ only).
    BEDROCK_MAX_TOKENS = _int_env("BEDROCK_MAX_TOKENS", 200)
    BEDROCK_TIMEOUT_SECONDS = _int_env("BEDROCK_TIMEOUT_SECONDS", 8)
