"""Unit tests for trusted-boundary input validation (TASKS.md 7.2, issue #56).

PRD §5.7: "Tool inputs validated (Pydantic models); web-search queries
length-capped". This is the **validation** posture — distinct from 7.1's
*sanitisation*. Where 7.1 silently neutralises untrusted text so it cannot act
as an instruction, 7.2 **rejects** abusive/oversized *direct user input* (the
topic, a search query) with a clear, typed, actionable error so the bad input
is surfaced rather than quietly mangled.

Written TDD-first (red before green). Every cap the assertions rely on comes
from :mod:`agent_debate.core.security.constants` (single source of truth), so
nothing is hard-coded here that the code does not also name.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    InvalidInputError,
    validate_search_query,
    validate_topic,
)
from agent_debate.core.security import (
    MAX_QUERY_LEN,
    MAX_TOPIC_LEN,
    SearchQueryInput,
    TopicInput,
)


def test_plain_topic_passes_and_is_returned_trimmed() -> None:
    """A benign topic validates and is returned (trimmed)."""
    out = validate_topic("  Should cities ban private cars?  ")
    assert out == "Should cities ban private cars?"


def test_overlength_topic_raises_with_cap_in_message() -> None:
    """An over-length topic raises a clear error naming the cap."""
    with pytest.raises(InvalidInputError) as excinfo:
        validate_topic("a" * (MAX_TOPIC_LEN + 1))
    message = str(excinfo.value)
    assert str(MAX_TOPIC_LEN) in message
    assert "topic" in message.lower()


def test_topic_with_control_char_is_rejected() -> None:
    """A topic carrying an ASCII control char is rejected (not stripped)."""
    with pytest.raises(InvalidInputError):
        validate_topic("hello\x00world")


def test_topic_with_ansi_escape_is_rejected() -> None:
    """A topic carrying an ANSI escape sequence is rejected."""
    with pytest.raises(InvalidInputError):
        validate_topic("hello\x1b[31mworld")


def test_empty_topic_is_rejected() -> None:
    """An empty topic is rejected with a clear error."""
    with pytest.raises(InvalidInputError):
        validate_topic("")


def test_whitespace_only_topic_is_rejected() -> None:
    """A whitespace-only topic is rejected (no usable content)."""
    with pytest.raises(InvalidInputError):
        validate_topic("   \t  ")


def test_plain_query_passes_and_is_returned() -> None:
    """A benign search query validates and is returned (trimmed)."""
    out = validate_search_query("  electric car adoption 2026 ")
    assert out == "electric car adoption 2026"


def test_overlength_query_raises_with_cap_in_message() -> None:
    """An over-length query raises a clear error naming the cap."""
    with pytest.raises(InvalidInputError) as excinfo:
        validate_search_query("a" * (MAX_QUERY_LEN + 1))
    message = str(excinfo.value)
    assert str(MAX_QUERY_LEN) in message
    assert "query" in message.lower()


def test_query_with_control_sequence_is_rejected() -> None:
    """A query carrying control/escape sequences is rejected."""
    with pytest.raises(InvalidInputError):
        validate_search_query("search\x1b[2Jterm")


def test_empty_query_is_rejected() -> None:
    """An empty query is rejected."""
    with pytest.raises(InvalidInputError):
        validate_search_query("   ")


def test_error_is_value_error_subclass() -> None:
    """The documented error is a ``ValueError`` subclass (clean, typed)."""
    assert issubclass(InvalidInputError, ValueError)


def test_error_message_is_actionable() -> None:
    """The rejection message names the field and is human-actionable."""
    with pytest.raises(InvalidInputError) as excinfo:
        validate_topic("a" * (MAX_TOPIC_LEN + 1))
    assert "exceeds" in str(excinfo.value).lower()


def test_caps_are_named_constants() -> None:
    """The caps are real, positive named constants (no inline magic)."""
    assert isinstance(MAX_TOPIC_LEN, int) and MAX_TOPIC_LEN > 0
    assert isinstance(MAX_QUERY_LEN, int) and MAX_QUERY_LEN > 0


def test_topic_pydantic_model_accepts_valid() -> None:
    """The Pydantic ``TopicInput`` model reuses the validator and accepts good input."""
    model = TopicInput(topic="Is nuclear power the safest energy source?")
    assert model.topic == "Is nuclear power the safest energy source?"


def test_topic_pydantic_model_rejects_control_char() -> None:
    """The Pydantic model rejects abusive input via the shared validator."""
    with pytest.raises(ValueError):  # noqa: PT011 - pydantic wraps as ValidationError
        TopicInput(topic="bad\x07topic")


def test_query_pydantic_model_rejects_overlength() -> None:
    """The Pydantic ``SearchQueryInput`` model rejects an over-length query."""
    with pytest.raises(ValueError):  # noqa: PT011 - pydantic wraps as ValidationError
        SearchQueryInput(query="a" * (MAX_QUERY_LEN + 1))
