"""Purpose: Fallback word selection from data/fallback_words.json.
Owner: Chris (backend).
"""

import json
import os
import random
import threading

FALLBACK_WORDS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "fallback_words.json",
)

RECENT_WORDS_PER_BUCKET = 5


def load_words(path=FALLBACK_WORDS_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class WordBank:
    """Picks a fallback word for a category/difficulty, avoiding words used
    recently in that same bucket where possible.
    """

    def __init__(self, words_by_bucket=None, recent_limit=RECENT_WORDS_PER_BUCKET):
        self._words = words_by_bucket if words_by_bucket is not None else load_words()
        self._recent_limit = recent_limit
        self._recent = {}
        self._lock = threading.Lock()

    def has_bucket(self, category, difficulty):
        return bool(self._words.get(category, {}).get(difficulty))

    def recent_words(self, category, difficulty):
        with self._lock:
            return list(self._recent.get((category, difficulty), []))

    def pick_word(self, category, difficulty):
        bucket = self._words.get(category, {}).get(difficulty)
        if not bucket:
            return None
        with self._lock:
            key = (category, difficulty)
            recent = self._recent.get(key, [])
            candidates = [word for word in bucket if word not in recent]
            if not candidates:
                candidates = list(bucket)
            word = random.choice(candidates)
            self._recent[key] = ([word] + recent)[: self._recent_limit]
            return word


word_bank = WordBank()
