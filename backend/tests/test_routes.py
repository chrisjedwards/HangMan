"""Purpose: Endpoint tests for routes/game.py and routes/health.py, run
against the Flask test client with MOCK_AI=true (the default config).
Owner: Chris (backend).
"""

import json
import re

from config import Config
from services.game_state import game_store


def start_game(client, category="programming_languages", difficulty="medium"):
    response = client.post(
        "/api/generate-word", json={"category": category, "difficulty": difficulty}
    )
    assert response.status_code == 200
    return response.get_json()


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_generate_word_returns_contract_shape(client):
    body = start_game(client)

    assert set(body.keys()) == {
        "game_id",
        "length",
        "category",
        "difficulty",
        "max_lives",
    }
    assert "word" not in body
    assert body["category"] == "programming_languages"
    assert body["difficulty"] == "medium"
    assert body["max_lives"] == Config.MAX_LIVES
    assert isinstance(body["length"], int) and body["length"] > 0


def test_generate_word_rejects_invalid_category(client):
    response = client.post(
        "/api/generate-word",
        json={"category": "not_a_category", "difficulty": "medium"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_guess_unknown_game_returns_game_not_found(client):
    response = client.post("/api/guess", json={"game_id": "0" * 32, "letter": "A"})

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "game_not_found"


def test_guess_invalid_letter_is_rejected(client):
    body = start_game(client)

    response = client.post(
        "/api/guess", json={"game_id": body["game_id"], "letter": "AB"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_full_game_flow_win(client):
    body = start_game(client, category="programming_languages", difficulty="easy")
    game_id = body["game_id"]
    word = game_store.get_game(game_id).word

    payload = None
    for letter in sorted(set(word)):
        response = client.post(
            "/api/guess", json={"game_id": game_id, "letter": letter}
        )
        assert response.status_code == 200
        payload = response.get_json()

    assert payload["status"] == "won"
    assert payload["word"] == word

    comment_response = client.post("/api/comment", json={"game_id": game_id})
    assert comment_response.status_code == 200
    comment_text = comment_response.get_json()["comment"]
    assert isinstance(comment_text, str) and comment_text != ""


def test_repeated_wrong_guess_costs_no_extra_life(client):
    body = start_game(client)
    game_id = body["game_id"]

    # "Q" does not appear in any word in fallback_words.json, so both guesses
    # are wrong, but only the first should cost a life.
    first = client.post("/api/guess", json={"game_id": game_id, "letter": "Q"})
    second = client.post("/api/guess", json={"game_id": game_id, "letter": "Q"})

    assert first.get_json()["lives_left"] == second.get_json()["lives_left"]
    assert second.get_json()["wrong_letters"] == ["Q"]


def test_comment_rejected_before_game_over(client):
    body = start_game(client)

    response = client.post("/api/comment", json={"game_id": body["game_id"]})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_hint_flow_and_limit(client):
    body = start_game(client)
    game_id = body["game_id"]
    max_hints = Config.MAX_HINTS

    hints_left_values = []
    for _ in range(max_hints):
        response = client.post("/api/hint", json={"game_id": game_id})
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload["hint"], str) and payload["hint"] != ""
        hints_left_values.append(payload["hints_left"])

    assert hints_left_values == list(range(max_hints - 1, -1, -1))

    over_limit = client.post("/api/hint", json={"game_id": game_id})
    assert over_limit.status_code == 400
    assert over_limit.get_json()["error"]["code"] == "invalid_request"


def test_hint_rejected_after_game_over(client):
    body = start_game(client, difficulty="easy")
    game_id = body["game_id"]
    word = game_store.get_game(game_id).word

    for letter in sorted(set(word)):
        client.post("/api/guess", json={"game_id": game_id, "letter": letter})

    response = client.post("/api/hint", json={"game_id": game_id})

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_request"


def test_unknown_api_path_returns_json_404(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_wrong_method_returns_json_405(client):
    response = client.get("/api/generate-word")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "method_not_allowed"


def test_rate_limit_returns_json_429(client):
    # The Limiter in extensions.py is a single shared instance (the standard
    # Flask-Limiter factory pattern), and it only reads RATELIMIT_DEFAULT
    # from the FIRST app that ever called init_app() on it in this process -
    # later apps with a different RATE_LIMIT are ignored. So instead of
    # spinning up an app with a smaller limit, this drives the real
    # configured RATE_LIMIT to its actual boundary. It must hit a route that
    # actually exists (default limits are only evaluated for a matched
    # endpoint) and one that isn't exempt (health.py exempts /api/health).
    limit = int(re.match(r"\d+", Config.RATE_LIMIT).group())
    body = {"category": "programming_languages", "difficulty": "easy"}

    responses = [client.post("/api/generate-word", json=body) for _ in range(limit)]
    assert all(response.status_code == 200 for response in responses)

    limited = client.post("/api/generate-word", json=body)

    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "rate_limited"


def test_secret_word_never_leaks_before_game_over(client):
    body = start_game(client, category="devops_tools", difficulty="hard")
    game_id = body["game_id"]
    word = game_store.get_game(game_id).word

    assert word not in json.dumps(body).upper()

    unique_letters = sorted(set(word))
    letters_to_guess, final_letter = unique_letters[:-1], unique_letters[-1]

    for letter in letters_to_guess:
        response = client.post(
            "/api/guess", json={"game_id": game_id, "letter": letter}
        )
        payload = response.get_json()
        assert payload["status"] == "playing"
        assert "word" not in payload
        assert word not in response.get_data(as_text=True).upper()

    wrong_letter = next(ch for ch in "QXZJ" if ch not in word)
    wrong_response = client.post(
        "/api/guess", json={"game_id": game_id, "letter": wrong_letter}
    )
    wrong_payload = wrong_response.get_json()
    assert wrong_payload["status"] == "playing"
    assert "word" not in wrong_payload
    assert word not in wrong_response.get_data(as_text=True).upper()

    for _ in range(Config.MAX_HINTS):
        hint_response = client.post("/api/hint", json={"game_id": game_id})
        assert word not in hint_response.get_data(as_text=True).upper()

    # Now finish the game and confirm the word IS revealed - proving the
    # checks above were meaningful rather than a check that never triggers.
    final_response = client.post(
        "/api/guess", json={"game_id": game_id, "letter": final_letter}
    )
    final_payload = final_response.get_json()
    assert final_payload["status"] == "won"
    assert final_payload["word"] == word
