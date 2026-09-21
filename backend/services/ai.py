"""Purpose: AI provider interface, mock implementation, and Bedrock stub.
Owner: Chris (backend).

MockAI never calls AWS and is selected whenever MOCK_AI=true. Its hints are
deliberately generic, category-level sentences that never reference the
specific secret word, so they cannot leak it. BedrockAI is a TODO for the
next step (real Bedrock Converse API calls); every method just raises
NotImplementedError for now.
"""

import random

from services.words import word_bank

HINTS_BY_CATEGORY = {
    "programming_languages": [
        "It's used to write instructions that a computer can execute.",
        "Developers reach for it when building software applications.",
        "You might see it listed as a required skill in a job posting.",
    ],
    "devops_tools": [
        "Teams use it to automate parts of building or running software.",
        "It's often part of a modern deployment pipeline.",
        "Platform engineers tend to rely on it daily.",
    ],
    "aws_services": [
        "It's part of Amazon's cloud computing platform.",
        "You might configure it from the AWS console or with Terraform.",
        "Cloud engineers use it to build scalable systems.",
    ],
    "linux_commands": [
        "You'd type it into a Linux or Unix terminal.",
        "System administrators use it to manage files or processes.",
        "It's commonly used inside shell scripts.",
    ],
}

DEFAULT_HINTS = [
    "It's a common term in modern software development.",
    "You'll likely run into it while working with technology stacks.",
]

WIN_COMMENTS = [
    "Nice work spelling {word}! Your debugging skills are showing.",
    "You cracked {word} with lives to spare. Well played!",
    "{word}, solved! Looks like your syntax skills are error-free today.",
]

LOSE_COMMENTS = [
    "So close! The word was {word}. Better luck on the next compile.",
    "Out of lives! The answer was {word} - worth a retry.",
    "{word} got the better of you this time, but every bug teaches something.",
]


class AIProvider:
    """Interface every AI backend must implement."""

    def generate_word(self, category, difficulty, recent_words=None):
        raise NotImplementedError

    def generate_hint(self, word, category, difficulty, hints_given=0):
        raise NotImplementedError

    def generate_comment(
        self,
        result,
        wrong_guesses,
        lives_left,
        max_lives,
        hints_used,
        difficulty,
        category,
        word,
    ):
        raise NotImplementedError


class MockAI(AIProvider):
    """Canned, varied responses used when MOCK_AI=true. No AWS calls."""

    def generate_word(self, category, difficulty, recent_words=None):
        return word_bank.pick_word(category, difficulty)

    def generate_hint(self, word, category, difficulty, hints_given=0):
        pool = HINTS_BY_CATEGORY.get(category, DEFAULT_HINTS)
        return pool[hints_given % len(pool)]

    def generate_comment(
        self,
        result,
        wrong_guesses,
        lives_left,
        max_lives,
        hints_used,
        difficulty,
        category,
        word,
    ):
        pool = WIN_COMMENTS if result == "won" else LOSE_COMMENTS
        return random.choice(pool).format(word=word)


class BedrockAI(AIProvider):
    """Real AWS Bedrock Converse API backend. Not implemented yet (step 2)."""

    def __init__(self, region=None, model_id=None):
        self.region = region
        self.model_id = model_id

    def generate_word(self, category, difficulty, recent_words=None):
        raise NotImplementedError("BedrockAI.generate_word is not implemented yet")

    def generate_hint(self, word, category, difficulty, hints_given=0):
        raise NotImplementedError("BedrockAI.generate_hint is not implemented yet")

    def generate_comment(
        self,
        result,
        wrong_guesses,
        lives_left,
        max_lives,
        hints_used,
        difficulty,
        category,
        word,
    ):
        raise NotImplementedError("BedrockAI.generate_comment is not implemented yet")


def create_ai_provider(mock_ai, region=None, model_id=None):
    if mock_ai:
        return MockAI()
    return BedrockAI(region=region, model_id=model_id)
