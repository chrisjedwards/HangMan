"""Purpose: Unit tests for services/ai.py:BedrockAI, using a hand-written
stub bedrock-runtime client so tests never make a real network call.
Owner: Chris (backend).

A stub (not moto) is used here: moto's Bedrock Converse support is
limited/immature, this only needs to control what one method (converse)
returns, and a plain class makes exactly what each test simulates obvious
at a glance - more useful here than emulating the full AWS API surface.
"""

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError

from services.ai import AIError, BedrockAI, _load_prompt


class StubBedrockClient:
    """Returns responses, or raises exceptions, from a queue - one per call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def bedrock_response(text, input_tokens=10, output_tokens=5):
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "usage": {"inputTokens": input_tokens, "outputTokens": output_tokens},
    }


def make_ai(responses, **kwargs):
    client = StubBedrockClient(responses)
    ai = BedrockAI(region="eu-north-1", model_id="fake-model", client=client, **kwargs)
    return ai, client


def test_real_prompt_files_load_and_parse():
    for filename in ("generate_word.md", "hint.md", "comment.md"):
        system_prompt, user_template = _load_prompt(filename)
        assert system_prompt
        assert "{{" in user_template


def test_construction_loads_all_three_prompts_without_network_call():
    ai, client = make_ai([])
    assert set(ai._prompts.keys()) == {"generate_word", "hint", "comment"}
    assert client.calls == []


# ---- generate_word ----


def test_generate_word_happy_path():
    ai, client = make_ai([bedrock_response('{"word": "PYTHON"}')])

    word = ai.generate_word("programming_languages", "medium", recent_words=["RUBY"])

    assert word == "PYTHON"
    assert len(client.calls) == 1


def test_generate_word_invalid_json_raises_ai_error_without_retry():
    ai, client = make_ai([bedrock_response("this is not json")])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "medium")

    assert len(client.calls) == 1


def test_generate_word_invalid_word_raises_ai_error_without_retry():
    # Too long and contains digits - fails validate_ai_word.
    ai, client = make_ai([bedrock_response('{"word": "not-a-valid-word-123"}')])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "medium")

    assert len(client.calls) == 1


def test_generate_word_wrong_length_for_difficulty_raises_ai_error():
    # "CAT" is well-formed but too short for "medium" (needs 6-8 letters).
    ai, client = make_ai([bedrock_response('{"word": "CAT"}')])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "medium")


def test_markdown_fenced_json_is_parsed():
    ai, client = make_ai([bedrock_response('```json\n{"word": "RUBY"}\n```')])

    word = ai.generate_word("programming_languages", "easy")

    assert word == "RUBY"


# ---- generate_hint ----


def test_generate_hint_happy_path():
    ai, client = make_ai(
        [bedrock_response('{"hint": "It compiles to bytecode."}')]
    )

    hint = ai.generate_hint("PYTHON", "programming_languages", "medium", hints_given=0)

    assert hint == "It compiles to bytecode."


def test_generate_hint_leaking_word_raises_ai_error_without_retry():
    ai, client = make_ai([bedrock_response('{"hint": "The word is PYTHON."}')])

    with pytest.raises(AIError):
        ai.generate_hint("PYTHON", "programming_languages", "medium", hints_given=0)

    assert len(client.calls) == 1


def test_generate_hint_empty_raises_ai_error():
    ai, client = make_ai([bedrock_response('{"hint": ""}')])

    with pytest.raises(AIError):
        ai.generate_hint("PYTHON", "programming_languages", "medium", hints_given=0)


# ---- generate_comment ----


def test_generate_comment_happy_path():
    ai, client = make_ai([bedrock_response('{"comment": "Nice work!"}')])

    comment = ai.generate_comment(
        "won", [], 4, 6, 1, "medium", "programming_languages", "PYTHON"
    )

    assert comment == "Nice work!"


def test_generate_comment_empty_raises_ai_error():
    ai, client = make_ai([bedrock_response('{"comment": ""}')])

    with pytest.raises(AIError):
        ai.generate_comment(
            "lost", ["Z"], 0, 6, 0, "medium", "programming_languages", "PYTHON"
        )


# ---- retry behavior ----


def test_transient_error_is_retried_once_then_succeeds():
    error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse"
    )
    ai, client = make_ai([error, bedrock_response('{"word": "RUBY"}')])

    word = ai.generate_word("programming_languages", "easy")

    assert word == "RUBY"
    assert len(client.calls) == 2


def test_transient_error_twice_exhausts_retry_and_raises():
    error = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}, "Converse"
    )
    ai, client = make_ai([error, error])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "easy")

    assert len(client.calls) == 2


def test_non_transient_client_error_is_never_retried():
    error = ClientError(
        {"Error": {"Code": "ValidationException", "Message": "bad input"}}, "Converse"
    )
    ai, client = make_ai([error, bedrock_response('{"word": "RUBY"}')])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "easy")

    # Only 1 call: a non-transient error must not consume the retry, and
    # must not reach the (would-be-valid) second queued response.
    assert len(client.calls) == 1


def test_read_timeout_is_treated_as_transient_and_retried():
    timeout = ReadTimeoutError(endpoint_url="https://bedrock.example.com")
    ai, client = make_ai([timeout, bedrock_response('{"word": "RUBY"}')])

    word = ai.generate_word("programming_languages", "easy")

    assert word == "RUBY"
    assert len(client.calls) == 2


def test_read_timeout_twice_raises_ai_error():
    timeout = ReadTimeoutError(endpoint_url="https://bedrock.example.com")
    ai, client = make_ai([timeout, timeout])

    with pytest.raises(AIError):
        ai.generate_word("programming_languages", "easy")

    assert len(client.calls) == 2


def test_max_tokens_from_config_is_passed_to_converse():
    ai, client = make_ai([bedrock_response('{"word": "RUBY"}')], max_tokens=123)

    ai.generate_word("programming_languages", "easy")

    assert client.calls[0]["inferenceConfig"]["maxTokens"] == 123
