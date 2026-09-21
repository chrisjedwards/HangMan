"""Purpose: Unit tests for services/game_state.py. Owner: Chris (backend)."""

import time

from services.game_state import GameStore, STATUS_LOST, STATUS_PLAYING, STATUS_WON


def make_store(**kwargs):
    return GameStore(**kwargs)


def test_create_game_starts_playing_with_full_lives():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    assert game.word == "PYTHON"
    assert game.lives == 6
    assert game.status == STATUS_PLAYING
    assert game.masked_word() == "_ _ _ _ _ _"


def test_masking_reveals_only_guessed_letters():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    store.guess_letter(game.game_id, "p")

    assert game.masked_word() == "P _ _ _ _ _"


def test_correct_guess_does_not_cost_a_life():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    _, correct = store.guess_letter(game.game_id, "P")

    assert correct is True
    assert game.lives == 6
    assert game.wrong_letters == []


def test_wrong_guess_costs_a_life_and_is_recorded():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    _, correct = store.guess_letter(game.game_id, "Z")

    assert correct is False
    assert game.lives == 5
    assert game.wrong_letters == ["Z"]


def test_repeated_wrong_guess_costs_no_extra_life():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    store.guess_letter(game.game_id, "Z")
    store.guess_letter(game.game_id, "Z")

    assert game.lives == 5
    assert game.wrong_letters == ["Z"]


def test_repeated_correct_guess_is_a_no_op():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    store.guess_letter(game.game_id, "P")
    store.guess_letter(game.game_id, "P")

    assert game.lives == 6
    assert game.masked_word() == "P _ _ _ _ _"


def test_guessing_every_letter_wins():
    store = make_store()
    game = store.create_game("CAT", "programming_languages", "easy", max_lives=6)

    for letter in "CAT":
        store.guess_letter(game.game_id, letter)

    assert game.status == STATUS_WON
    assert game.masked_word() == "C A T"


def test_running_out_of_lives_loses():
    store = make_store()
    game = store.create_game("CAT", "programming_languages", "easy", max_lives=2)

    store.guess_letter(game.game_id, "X")
    store.guess_letter(game.game_id, "Y")

    assert game.status == STATUS_LOST
    assert game.lives == 0


def test_guess_after_game_over_does_not_change_state():
    store = make_store()
    game = store.create_game("CAT", "programming_languages", "easy", max_lives=1)

    store.guess_letter(game.game_id, "Z")  # loses immediately
    assert game.status == STATUS_LOST

    store.guess_letter(game.game_id, "C")

    assert game.status == STATUS_LOST
    assert game.masked_word() == "_ _ _"


def test_guess_on_unknown_game_returns_none():
    store = make_store()

    game, correct = store.guess_letter("does-not-exist", "A")

    assert game is None
    assert correct is None


def test_get_game_returns_none_for_unknown_id():
    store = make_store()

    assert store.get_game("does-not-exist") is None


def test_hint_usage_is_capped_by_max_hints():
    store = make_store()
    game = store.create_game("PYTHON", "programming_languages", "medium", max_lives=6)

    _, first = store.use_hint(game.game_id, max_hints=2)
    _, second = store.use_hint(game.game_id, max_hints=2)
    _, third = store.use_hint(game.game_id, max_hints=2)

    assert (first, second, third) == (True, True, False)
    assert game.hints_used == 2


def test_games_expire_after_ttl():
    store = make_store(ttl_seconds=0.05)
    game = store.create_game("CAT", "programming_languages", "easy", max_lives=6)

    time.sleep(0.1)

    assert store.get_game(game.game_id) is None
    assert store.count() == 0


def test_max_games_cap_evicts_oldest():
    store = make_store(max_games=2)

    first = store.create_game("CAT", "programming_languages", "easy", max_lives=6)
    time.sleep(0.01)
    store.create_game("DOG", "programming_languages", "easy", max_lives=6)
    time.sleep(0.01)
    store.create_game("BAT", "programming_languages", "easy", max_lives=6)

    assert store.count() == 2
    assert store.get_game(first.game_id) is None
