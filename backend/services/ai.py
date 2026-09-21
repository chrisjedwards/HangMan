"""Purpose: AI provider interface, mock implementation, and real Bedrock
backend. Owner: Chris (backend).

MockAI never calls AWS and is selected whenever MOCK_AI=true. Its hints are
deliberately generic, category-level sentences that never reference the
specific secret word, so they cannot leak it. BedrockAI calls AWS Bedrock's
Converse API using the three prompt templates in backend/prompts/*.md,
loaded once at construction time (not per-request). Every value it returns
is validated with the same utils.validators functions the routes already
trust for MockAI, so BedrockAI can never hand back something the contract
wouldn't allow - it raises AIError instead.
"""

import json
import logging
import random
import re
import string
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from botocore.exceptions import ConnectionError as BotoConnectionError
from botocore.exceptions import ReadTimeoutError

from services.words import word_bank
from utils.validators import hint_contains_word, validate_ai_word

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_SYSTEM_PROMPT_RE = re.compile(r"## System prompt\n\n(.+?)\n\n##", re.DOTALL)
_USER_TEMPLATE_RE = re.compile(
    r"## User prompt template\n\n```text\n(.+?)\n```", re.DOTALL
)
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def _load_prompt(filename):
    """Parse a prompts/*.md file into (system_prompt, user_template).

    Raises ValueError at startup (not per-request) if a prompt file's
    structure doesn't match what's expected, so a broken .md file is caught
    immediately instead of failing confusingly on the first real request.
    """
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")

    system_match = _SYSTEM_PROMPT_RE.search(text)
    user_match = _USER_TEMPLATE_RE.search(text)
    if not system_match or not user_match:
        raise ValueError(f"Could not parse prompt template structure from {filename}")

    return system_match.group(1).strip(), user_match.group(1).strip()


def _fill_template(template, **values):
    def replace(match):
        key = match.group(1)
        if key not in values:
            raise KeyError(f"Missing template value for {{{{{key}}}}}")
        return str(values[key])

    return _PLACEHOLDER_RE.sub(replace, template)

# Bedrock error codes worth retrying once - transient service-side hiccups,
# not something a retry can't fix (those raise immediately, see _invoke).
TRANSIENT_ERROR_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelTimeoutException",
}


class AIError(Exception):
    """Raised when an AI provider fails to produce usable output.

    Routes catch this specifically (never a bare Exception) so a genuine bug
    elsewhere still surfaces as a 500 instead of being silently treated as
    "the AI failed, fall back".
    """

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


def _parse_json_response(text):
    """Parse the model's text output as JSON, stripping a markdown code
    fence if the model wrapped its answer in one despite being told not to.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AIError(f"Model returned invalid JSON: {exc}") from exc


def _extract_text(response):
    """Pull the assistant's text out of a Bedrock Converse API response."""
    try:
        return response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError(f"Unexpected Bedrock response shape: {exc}") from exc


class BedrockAI(AIProvider):
    """Real AWS Bedrock Converse API backend, using the prompt templates in
    backend/prompts/*.md.
    """

    def __init__(
        self,
        region=None,
        model_id=None,
        max_tokens=200,
        timeout_seconds=8,
        client=None,
    ):
        self.region = region
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        # Injectable so tests can pass a stub instead of a real boto3
        # client - see backend/tests/test_ai.py. boto3.client() does not
        # itself make a network call or check credentials, so constructing
        # the real client here at startup is safe even before MOCK_AI=false
        # is actually used against real Bedrock.
        self._client = client or boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=BotoConfig(connect_timeout=3, read_timeout=timeout_seconds),
        )
        # Loaded once here, not per-request - see module docstring.
        self._prompts = {
            "generate_word": _load_prompt("generate_word.md"),
            "hint": _load_prompt("hint.md"),
            "comment": _load_prompt("comment.md"),
        }

    def _invoke(self, system_prompt, user_prompt):
        """Call Bedrock Converse, retrying once on a transient error only.

        A validation failure (invalid JSON, bad word, leaking hint) is never
        retried - retrying would just spend money asking the same broken
        question again. Only network hiccups and known-transient Bedrock
        error codes get a single retry.
        """
        last_error = None
        for attempt in (1, 2):
            try:
                response = self._client.converse(
                    modelId=self.model_id,
                    system=[{"text": system_prompt}],
                    messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                    inferenceConfig={
                        "maxTokens": self.max_tokens,
                        "temperature": 0.7,
                    },
                )
                usage = response.get("usage", {})
                logger.info(
                    "Bedrock call succeeded on attempt %d, usage=%s", attempt, usage
                )
                return response
            except (BotoConnectionError, ReadTimeoutError) as exc:
                last_error = exc
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code", "")
                last_error = exc
                if error_code not in TRANSIENT_ERROR_CODES:
                    raise AIError(f"Bedrock request failed: {exc}") from exc

            if attempt == 1:
                logger.warning(
                    "Bedrock call failed on attempt 1, retrying once: %s", last_error
                )

        raise AIError(f"Bedrock request failed after retry: {last_error}") from last_error

    def generate_word(self, category, difficulty, recent_words=None):
        system_prompt, user_template = self._prompts["generate_word"]
        user_prompt = _fill_template(
            user_template,
            category=category,
            difficulty=difficulty,
            seed_letter=random.choice(string.ascii_uppercase),
            recent_words=", ".join(recent_words) if recent_words else "none",
        )
        response = self._invoke(system_prompt, user_prompt)
        data = _parse_json_response(_extract_text(response))
        word = data.get("word") if isinstance(data, dict) else None

        if not validate_ai_word(word, difficulty):
            raise AIError(f"Model returned an invalid word: {word!r}")

        return word.strip().upper()

    def generate_hint(self, word, category, difficulty, hints_given=0):
        system_prompt, user_template = self._prompts["hint"]
        user_prompt = _fill_template(
            user_template,
            secret_word=word,
            category=category,
            difficulty=difficulty,
            hints_given=hints_given,
        )
        response = self._invoke(system_prompt, user_prompt)
        data = _parse_json_response(_extract_text(response))
        hint = data.get("hint") if isinstance(data, dict) else None

        if not hint or not isinstance(hint, str) or hint_contains_word(hint, word):
            raise AIError("Model returned an empty or word-leaking hint")

        return hint.strip()

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
        system_prompt, user_template = self._prompts["comment"]
        user_prompt = _fill_template(
            user_template,
            result=result,
            wrong_guesses=", ".join(wrong_guesses) if wrong_guesses else "none",
            lives_left=lives_left,
            max_lives=max_lives,
            hints_used=hints_used,
            difficulty=difficulty,
            category=category,
            word=word,
        )
        response = self._invoke(system_prompt, user_prompt)
        data = _parse_json_response(_extract_text(response))
        comment = data.get("comment") if isinstance(data, dict) else None

        if not comment or not isinstance(comment, str):
            raise AIError("Model returned an empty comment")

        return comment.strip()


def create_ai_provider(
    mock_ai, region=None, model_id=None, max_tokens=200, timeout_seconds=8
):
    if mock_ai:
        return MockAI()
    return BedrockAI(
        region=region,
        model_id=model_id,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )
