"""Purpose: Route-level tests for AI failure handling - generate-word
falling back to fallback_words.json, and hint/comment returning a 502
ai_unavailable error instead of inventing fallback text. Uses a fake
AIProvider (not BedrockAI) since these tests are about routes/game.py's own
behavior, not about Bedrock itself - see test_ai.py for BedrockAI's unit
tests with a stubbed boto3 client. Owner: Chris (backend).
"""

from services.ai import AIError, AIProvider
from services.game_state import game_store
from services.words import load_words

# Guaranteed absent from every word in this bucket (verified against
# data/fallback_words.json), so guessing all six always loses deterministically
# regardless of which word was picked.
GUARANTEED_WRONG_LETTERS = "DGMQXZ"


class FailingAI(AIProvider):
    """Always raises AIError, simulating an exhausted-retry Bedrock failure."""

    def generate_word(self, category, difficulty, recent_words=None):
        raise AIError("simulated Bedrock failure")

    def generate_hint(self, word, category, difficulty, hints_given=0):
        raise AIError("simulated Bedrock failure")

    def generate_comment(self, *args, **kwargs):
        raise AIError("simulated Bedrock failure")


class LeakingHintAI(AIProvider):
    """Returns a hint that leaks the word, without BedrockAI's own check -
    used to confirm the route's own defense-in-depth check also catches it.
    """

    def generate_word(self, category, difficulty, recent_words=None):
        raise NotImplementedError

    def generate_hint(self, word, category, difficulty, hints_given=0):
        return f"The word is {word}."

    def generate_comment(self, *args, **kwargs):
        raise NotImplementedError


def _start_game(client, category="programming_languages", difficulty="easy"):
    response = client.post(
        "/api/generate-word", json={"category": category, "difficulty": difficulty}
    )
    assert response.status_code == 200
    return response.get_json()


def _lose_game(client, game_id):
    for letter in GUARANTEED_WRONG_LETTERS:
        client.post("/api/guess", json={"game_id": game_id, "letter": letter})


def test_generate_word_falls_back_to_fallback_words_on_ai_error(client):
    client.application.config["AI_PROVIDER"] = FailingAI()

    response = client.post(
        "/api/generate-word",
        json={"category": "programming_languages", "difficulty": "easy"},
    )

    assert response.status_code == 200
    body = response.get_json()
    word = game_store.get_game(body["game_id"]).word
    fallback_bucket = load_words()["programming_languages"]["easy"]
    assert word in fallback_bucket


def test_hint_returns_502_ai_unavailable_on_ai_error(client):
    body = _start_game(client)
    client.application.config["AI_PROVIDER"] = FailingAI()

    response = client.post("/api/hint", json={"game_id": body["game_id"]})

    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "ai_unavailable"


def test_comment_returns_502_ai_unavailable_on_ai_error(client):
    body = _start_game(client)
    game_id = body["game_id"]
    _lose_game(client, game_id)
    assert game_store.get_game(game_id).status == "lost"

    client.application.config["AI_PROVIDER"] = FailingAI()
    response = client.post("/api/comment", json={"game_id": game_id})

    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "ai_unavailable"


def test_hint_leaking_the_word_is_rejected_not_sent_to_client(client):
    body = _start_game(client)
    game_id = body["game_id"]
    word = game_store.get_game(game_id).word
    client.application.config["AI_PROVIDER"] = LeakingHintAI()

    response = client.post("/api/hint", json={"game_id": game_id})

    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "ai_unavailable"
    # The leaking hint text must never reach the client, in any form.
    assert word not in response.get_data(as_text=True).upper()
