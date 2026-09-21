"""Purpose: Request body validation and AI-output validation helpers.
Owner: Chris (backend).
"""

import re

from utils.errors import ApiError

CATEGORIES = {
    "programming_languages",
    "devops_tools",
    "aws_services",
    "linux_commands",
}

DIFFICULTIES = {"easy", "medium", "hard"}

# Loosely matches backend/prompts/generate_word.md's length guidance; used
# only to sanity-check AI-produced words before they become the secret word.
DIFFICULTY_LENGTH_RANGES = {
    "easy": (4, 6),
    "medium": (6, 8),
    "hard": (8, 10),
}

MAX_WORD_LENGTH = 10

_LETTER_RE = re.compile(r"^[A-Za-z]$")
_WORD_RE = re.compile(r"^[A-Z]+$")
_GAME_ID_RE = re.compile(r"^[0-9a-f]{32}$")  # matches uuid.uuid4().hex


def _require_dict(data):
    if not isinstance(data, dict):
        raise ApiError("invalid_request", "A JSON body is required")


def validate_category_and_difficulty(data):
    _require_dict(data)
    category = data.get("category")
    difficulty = data.get("difficulty")
    if category not in CATEGORIES or difficulty not in DIFFICULTIES:
        raise ApiError("invalid_request", "category and difficulty are required")
    return category, difficulty


def validate_game_id(data):
    _require_dict(data)
    game_id = data.get("game_id")
    if not isinstance(game_id, str) or not _GAME_ID_RE.match(game_id):
        raise ApiError("invalid_request", "game_id is required")
    return game_id


def validate_letter(data):
    _require_dict(data)
    letter = data.get("letter")
    if not isinstance(letter, str) or not _LETTER_RE.match(letter):
        raise ApiError("invalid_request", "letter must be a single A-Z character")
    return letter.upper()


def validate_ai_word(word, difficulty):
    """True if an AI-produced word is safe to use as the secret word."""
    if not isinstance(word, str):
        return False
    word = word.strip().upper()
    if not _WORD_RE.match(word) or len(word) > MAX_WORD_LENGTH:
        return False
    min_len, max_len = DIFFICULTY_LENGTH_RANGES.get(difficulty, (1, MAX_WORD_LENGTH))
    return min_len <= len(word) <= max_len


def hint_contains_word(hint, word):
    """True if the hint text leaks the secret word (case-insensitive)."""
    if not isinstance(hint, str) or not isinstance(word, str) or not word:
        return False
    return word.strip().upper() in hint.upper()
