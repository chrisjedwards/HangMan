"""Purpose: Game endpoints - generate-word, guess, hint, comment.
Owner: Chris (backend).
"""

from flask import Blueprint, current_app, jsonify, request

from services.ai import AIError
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
    except AIError:
        # AI failure falls back to the fallback word list below - this is
        # the "fallback words" safeguard called for in CLAUDE.md. A bug
        # elsewhere (not an AIError) is deliberately NOT caught here, so it
        # still surfaces as a 500 instead of being masked as "AI failed".
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
    hints_given = game.hints_used - 1  # hints given before this one
    try:
        hint_text = ai.generate_hint(game.word, game.category, game.difficulty, hints_given)
    except AIError as exc:
        # No fallback text for hints - inventing text here would mean the
        # player can't tell an AI-authored hint from a made-up one. The
        # already-consumed hint attempt is a known, accepted trade-off (see
        # docs/implementation.md); avoiding it would need a refund path that
        # risks a race with concurrent requests for no real benefit here.
        raise ApiError(
            "ai_unavailable", "The hint service is temporarily unavailable", 502
        ) from exc

    if hint_contains_word(hint_text, game.word):
        # Defense in depth: BedrockAI already checks this itself, but the
        # secret word is never trusted blindly at the point it could leak.
        raise ApiError(
            "ai_unavailable", "The hint service is temporarily unavailable", 502
        )

    return jsonify(
        {"hint": hint_text.strip(), "hints_left": max_hints - game.hints_used}
    )


@game_bp.route("/comment", methods=["POST"])
def comment():
    data = request.get_json(silent=True)
    game_id = validate_game_id(data)

    game = _get_game_or_404(game_id)
    if game.status == STATUS_PLAYING:
        raise ApiError("invalid_request", "The game is not over yet", 400)

    ai = current_app.config["AI_PROVIDER"]
    try:
        comment_text = ai.generate_comment(
            game.status,
            game.wrong_letters,
            game.lives,
            game.max_lives,
            game.hints_used,
            game.difficulty,
            game.category,
            game.word,
        )
    except AIError as exc:
        # No invented fallback text here either - see the hint endpoint.
        raise ApiError(
            "ai_unavailable", "The comment service is temporarily unavailable", 502
        ) from exc

    return jsonify({"comment": comment_text.strip()})
