"""Purpose: Unit tests for utils/validators.py. Owner: Chris (backend)."""

import uuid

import pytest

from utils.errors import ApiError
from utils.validators import (
    hint_contains_word,
    validate_ai_word,
    validate_category_and_difficulty,
    validate_game_id,
    validate_letter,
)


def test_validate_category_and_difficulty_accepts_known_values():
    category, difficulty = validate_category_and_difficulty(
        {"category": "programming_languages", "difficulty": "medium"}
    )

    assert (category, difficulty) == ("programming_languages", "medium")


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"category": "programming_languages"},
        {"difficulty": "medium"},
        {"category": "not_a_category", "difficulty": "medium"},
        {"category": "programming_languages", "difficulty": "impossible"},
        "not a dict",
        None,
    ],
)
def test_validate_category_and_difficulty_rejects_bad_input(body):
    with pytest.raises(ApiError) as exc_info:
        validate_category_and_difficulty(body)

    assert exc_info.value.code == "invalid_request"


def test_validate_game_id_accepts_uuid4_hex():
    game_id = uuid.uuid4().hex

    assert validate_game_id({"game_id": game_id}) == game_id


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"game_id": ""},
        {"game_id": "not-a-real-id"},
        {"game_id": 12345},
        None,
    ],
)
def test_validate_game_id_rejects_bad_input(body):
    with pytest.raises(ApiError) as exc_info:
        validate_game_id(body)

    assert exc_info.value.code == "invalid_request"


def test_validate_letter_accepts_and_normalizes_single_letter():
    assert validate_letter({"letter": "p"}) == "P"
    assert validate_letter({"letter": "P"}) == "P"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"letter": ""},
        {"letter": "PY"},
        {"letter": "1"},
        {"letter": "!"},
        {"letter": 5},
        None,
    ],
)
def test_validate_letter_rejects_bad_input(body):
    with pytest.raises(ApiError) as exc_info:
        validate_letter(body)

    assert exc_info.value.code == "invalid_request"


@pytest.mark.parametrize(
    "word,difficulty,expected",
    [
        ("PYTHON", "medium", True),
        ("python", "medium", True),  # normalized before checking
        ("CAT", "medium", False),  # too short for medium
        ("SUPERCALIFRAG", "hard", False),  # over MAX_WORD_LENGTH
        ("PY7HON", "medium", False),  # contains a digit
        ("PY THON", "medium", False),  # contains a space
        (None, "medium", False),
    ],
)
def test_validate_ai_word(word, difficulty, expected):
    assert validate_ai_word(word, difficulty) is expected


def test_hint_contains_word_detects_leak_case_insensitively():
    assert hint_contains_word("It rhymes with python!", "PYTHON") is True
    assert hint_contains_word("A popular scripting language.", "PYTHON") is False
