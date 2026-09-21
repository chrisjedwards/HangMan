"""Purpose: Game endpoints - generate-word, guess, hint, comment.
Owner: Chris (backend).
"""

from flask import Blueprint, current_app, jsonify, request

from services.game_state import STATUS_PLAYING, game_store
from services.words import word_bank
from utils.errors import ApiError
from utils.validators import (
    hint_contains_word,
    validate_ai_word,
    validate_category_and_difficulty,
    validate_game_id,
    validate_letter,
)

game_bp = Blueprint("game", __name__)


def _get_game_or_404(game_id):
    game = game_store.get_game(game_id)
    if game is None:
        raise ApiError(
            "game_not_found", "The game does not exist or has expired", 404
        )
    return game


@game_bp.route("/generate-word", methods=["POST"])
def generate_word():
    data = request.get_json(silent=True)
    category, difficulty = validate_category_and_difficulty(data)

    ai = current_app.config["AI_PROVIDER"]
    word = None
    try:
        recent_words = word_bank.recent_words(category, difficulty)
        candidate = ai.generate_word(category, difficulty, recent_words)
        if validate_ai_word(candidate, difficulty):
            word = candidate.strip().upper()
    except Exception:
        # AI failure of any kind falls back to the fallback word list below -
        # this is the "fallback words" safeguard called for in CLAUDE.md.
        word = None

    if word is None:
        word = word_bank.pick_word(category, difficulty)

    if word is None:
        raise ApiError(
            "invalid_request",
            "No words available for that category and difficulty",
            400,
        )

    max_lives = current_app.config["MAX_LIVES"]
    game = game_store.create_game(word, category, difficulty, max_lives)

    return jsonify(
        {
            "game_id": game.game_id,
            "length": len(game.word),
            "category": game.category,
            "difficulty": game.difficulty,
            "max_lives": game.max_lives,
        }
    )


@game_bp.route("/guess", methods=["POST"])
def guess():
    data = request.get_json(silent=True)
    game_id = validate_game_id(data)
    letter = validate_letter(data)

    _get_game_or_404(game_id)
    game, correct = game_store.guess_letter(game_id, letter)

    response = {
        "masked_word": game.masked_word(),
        "correct": correct,
        "wrong_letters": game.wrong_letters,
        "lives_left": game.lives,
        "status": game.status,
    }
    if game.status != STATUS_PLAYING:
        response["word"] = game.word

    return jsonify(response)


@game_bp.route("/hint", methods=["POST"])
def hint():
    data = request.get_json(silent=True)
    game_id = validate_game_id(data)

    game = _get_game_or_404(game_id)
    if game.status != STATUS_PLAYING:
        raise ApiError("invalid_request", "The game is already over", 400)

    max_hints = current_app.config["MAX_HINTS"]
    game, allowed = game_store.use_hint(game_id, max_hints)
    if not allowed:
        raise ApiError("invalid_request", "No hints left", 400)

    ai = current_app.config["AI_PROVIDER"]
    hint_text = None
    try:
        hints_given = game.hints_used - 1  # hints given before this one
        candidate = ai.generate_hint(game.word, game.category, game.difficulty, hints_given)
        if candidate and not hint_contains_word(candidate, game.word):
            hint_text = candidate.strip()
    except Exception:
        hint_text = None

    if not hint_text:
        hint_text = "No hint is available right now, but you've got this."

    return jsonify({"hint": hint_text, "hints_left": max_hints - game.hints_used})


@game_bp.route("/comment", methods=["POST"])
def comment():
    data = request.get_json(silent=True)
    game_id = validate_game_id(data)

    game = _get_game_or_404(game_id)
    if game.status == STATUS_PLAYING:
        raise ApiError("invalid_request", "The game is not over yet", 400)

    ai = current_app.config["AI_PROVIDER"]
    comment_text = None
    try:
        candidate = ai.generate_comment(
            game.status,
            game.wrong_letters,
            game.lives,
            game.max_lives,
            game.hints_used,
            game.difficulty,
            game.category,
            game.word,
        )
        comment_text = candidate.strip() if candidate else None
    except Exception:
        comment_text = None

    if not comment_text:
        comment_text = (
            "Nice game!"
            if game.status == "won"
            else "Good try - better luck next time!"
        )

    return jsonify({"comment": comment_text})
