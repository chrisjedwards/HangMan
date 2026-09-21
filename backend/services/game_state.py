"""Purpose: In-memory game state store and core Hangman game rules.
Owner: Chris (backend).

Framework-free by design: no Flask or config imports, so it stays a pure,
directly unit-testable module. State lives only in this process's memory,
which is why production must run gunicorn with a single worker (see the
note in config.py and docs/implementation.md).
"""

import threading
import time
import uuid
from dataclasses import dataclass, field

GAME_TTL_SECONDS = 2 * 60 * 60  # expire games after ~2 hours of inactivity
MAX_GAMES = 500  # cap total stored games so memory cannot grow unbounded

STATUS_PLAYING = "playing"
STATUS_WON = "won"
STATUS_LOST = "lost"


@dataclass
class Game:
    game_id: str
    word: str
    category: str
    difficulty: str
    max_lives: int
    lives: int
    guessed_letters: set = field(default_factory=set)
    wrong_letters: list = field(default_factory=list)
    hints_used: int = 0
    status: str = STATUS_PLAYING
    created_at: float = field(default_factory=time.time)

    def masked_word(self):
        return " ".join(
            letter if letter in self.guessed_letters else "_"
            for letter in self.word
        )

    def is_over(self):
        return self.status != STATUS_PLAYING


class GameStore:
    """Thread-safe in-memory store of Game objects keyed by game_id."""

    def __init__(self, ttl_seconds=GAME_TTL_SECONDS, max_games=MAX_GAMES):
        self._games = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._max_games = max_games

    def _get_live_locked(self, game_id):
        """Return the game if present and not expired; evict it otherwise.

        Caller must hold self._lock.
        """
        game = self._games.get(game_id)
        if game is None:
            return None
        if time.time() - game.created_at > self._ttl_seconds:
            del self._games[game_id]
            return None
        return game

    def _purge_expired_locked(self):
        now = time.time()
        expired = [
            game_id
            for game_id, game in self._games.items()
            if now - game.created_at > self._ttl_seconds
        ]
        for game_id in expired:
            del self._games[game_id]

    def create_game(self, word, category, difficulty, max_lives):
        with self._lock:
            self._purge_expired_locked()
            if len(self._games) >= self._max_games:
                oldest_id = min(
                    self._games, key=lambda gid: self._games[gid].created_at
                )
                del self._games[oldest_id]
            game_id = uuid.uuid4().hex
            game = Game(
                game_id=game_id,
                word=word.upper(),
                category=category,
                difficulty=difficulty,
                max_lives=max_lives,
                lives=max_lives,
            )
            self._games[game_id] = game
            return game

    def get_game(self, game_id):
        with self._lock:
            return self._get_live_locked(game_id)

    def count(self):
        with self._lock:
            return len(self._games)

    def guess_letter(self, game_id, letter):
        """Apply one guessed letter. Returns (game, correct) or (None, None)
        if the game does not exist or has expired.

        A letter already guessed (right or wrong) never costs another life.
        Guessing after the game is already over leaves state unchanged.
        """
        letter = letter.upper()
        with self._lock:
            game = self._get_live_locked(game_id)
            if game is None:
                return None, None

            correct = letter in game.word
            if game.status != STATUS_PLAYING:
                return game, correct

            if correct:
                game.guessed_letters.add(letter)
            elif letter not in game.wrong_letters:
                game.wrong_letters.append(letter)
                game.lives -= 1

            if all(ch in game.guessed_letters for ch in game.word):
                game.status = STATUS_WON
            elif game.lives <= 0:
                game.status = STATUS_LOST

            return game, correct

    def use_hint(self, game_id, max_hints):
        """Consume one hint if under max_hints. Returns (game, allowed) or
        (None, None) if the game does not exist or has expired.
        """
        with self._lock:
            game = self._get_live_locked(game_id)
            if game is None:
                return None, None
            if game.hints_used >= max_hints:
                return game, False
            game.hints_used += 1
            return game, True


game_store = GameStore()
