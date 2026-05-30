"""Trusted-boundary input validation (PRD §5.7, task 7.2).

This is the **validation** half of Epic 7's security seam, and it is a *different
posture* from the 7.1 sanitiser. The sanitiser (:mod:`.sanitiser`) handles
*untrusted* text (web-search results, model output) by silently neutralising and
truncating it so it cannot act as an instruction. The validators here handle
*direct user input* at a trusted boundary — the debate **topic** and a
**search query** — and **reject** abusive/oversized input with a clear, typed,
actionable error so the bad input is surfaced rather than quietly mangled.

Concretely they enforce three rules (all caps live in :mod:`.constants`, the
single source of truth — no inline magic, guideline §7.2):

1. **Length cap** — reject input longer than its named cap
   (:data:`~constants.MAX_TOPIC_LEN` / :data:`~constants.MAX_QUERY_LEN`).
2. **Charset / control-sequence rejection** — reject any ASCII control char or
   ANSI/terminal escape sequence (printable text only). Distinct from 7.1, which
   *strips* these silently; here they are surfaced as an error.
3. **Non-empty** — reject empty / whitespace-only input.

Pure text processing — no network, no config files read at call time. The
:class:`TopicInput` / :class:`SearchQueryInput` Pydantic models reuse the same
functions so the API/CLI layers validate "tool inputs" (PRD §5.7) consistently.
"""

from __future__ import annotations

import re

from agent_debate.core.security import constants
from pydantic import BaseModel, field_validator


class InvalidInputError(ValueError):
    """Raised when direct user input fails validation (task 7.2).

    A :class:`ValueError` subclass so callers can catch it narrowly *or* as the
    broad family, while the message stays clear and actionable (naming the field
    and the limit) — we never leak a deep stack trace to the user.
    """


#: Matches any ASCII C0/C1 control character (incl. ESC ``\x1b``, NUL, BEL) plus
#: the DEL char. ANSI escape sequences always *begin* with ESC, so detecting any
#: control char is sufficient to reject them. Single source for the rule.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _reject_if_empty(value: str, field: str) -> str:
    """Return ``value`` trimmed, or raise if it is empty / whitespace-only."""
    trimmed = value.strip()
    if not trimmed:
        raise InvalidInputError(f"{field} must not be empty or whitespace-only.")
    return trimmed


def _reject_control_chars(value: str, field: str) -> None:
    """Raise if ``value`` contains any ASCII control / escape character."""
    if _CONTROL_CHARS.search(value):
        raise InvalidInputError(
            f"{field} contains control or escape characters; printable text only is allowed."
        )


def _reject_if_too_long(value: str, field: str, cap: int) -> None:
    """Raise if ``value`` exceeds ``cap`` characters (message names the cap)."""
    if len(value) > cap:
        raise InvalidInputError(
            f"{field} exceeds the maximum length of {cap} characters "
            f"(got {len(value)}); please shorten it."
        )


def validate_topic(topic: str) -> str:
    """Validate a user-supplied debate ``topic``; return it trimmed or raise.

    Enforces, in order: non-empty, no control/escape chars, length within
    :data:`constants.MAX_TOPIC_LEN`. Raises :class:`InvalidInputError` (a clear,
    actionable ``ValueError`` subclass) on the first failing rule.
    """
    _reject_control_chars(topic, "Topic")
    trimmed = _reject_if_empty(topic, "Topic")
    _reject_if_too_long(trimmed, "Topic", constants.MAX_TOPIC_LEN)
    return trimmed


def validate_search_query(query: str) -> str:
    """Validate a web-search ``query``; return it trimmed or raise.

    Enforces, in order: non-empty, no control/escape sequences, length within
    :data:`constants.MAX_QUERY_LEN` (PRD §5.7: "web-search queries
    length-capped"). Raises :class:`InvalidInputError` on the first failure.
    """
    _reject_control_chars(query, "Search query")
    trimmed = _reject_if_empty(query, "Search query")
    _reject_if_too_long(trimmed, "Search query", constants.MAX_QUERY_LEN)
    return trimmed


class TopicInput(BaseModel):
    """Pydantic model wrapping :func:`validate_topic` (PRD §5.7 tool inputs).

    Lets the API/CLI layers validate a topic field declaratively while reusing
    the exact same rules; the field validator stores the trimmed, checked value.
    """

    topic: str

    @field_validator("topic")
    @classmethod
    def _check_topic(cls, value: str) -> str:
        return validate_topic(value)


class SearchQueryInput(BaseModel):
    """Pydantic model wrapping :func:`validate_search_query` (tool-input validation)."""

    query: str

    @field_validator("query")
    @classmethod
    def _check_query(cls, value: str) -> str:
        return validate_search_query(value)


__all__ = [
    "InvalidInputError",
    "SearchQueryInput",
    "TopicInput",
    "validate_search_query",
    "validate_topic",
]
