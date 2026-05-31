"""Security gatekeeper subpackage — sanitises untrusted text (PRD §5.7, Epic 7).

This is the **security** gatekeeper: every piece of external text (the user
topic, **web-search results**, model output) passes through here and is
*normalised + injection-neutralised + length-capped* before it can re-enter a
prompt. It is **distinct** from the API/rate-limit gatekeeper at
:mod:`agent_debate.core.gatekeeper` (Epic 13). Pure text processing — it makes
no network call (the ``web_search`` skill, task 4.1, routes results through it).

Task 7.1 ships the sanitiser and 7.2 the *validators* (:mod:`.validation`):
these **reject** abusive/oversized *direct user input* (topic, search query)
with a clear, typed :class:`~.validation.InvalidInputError`, a distinct posture
from 7.1's silent neutralisation of *untrusted* text. Later Epic 7 tasks build
on this seam: 7.3 (no code execution), 7.4 (secret hygiene), 7.5 (security
tests). The re-exports below are the public surface;
:mod:`agent_debate.core` re-exports them again so callers reach them as
``agent_debate.core.sanitize_untrusted_text`` / ``SecurityGatekeeper``.
"""

from __future__ import annotations

from agent_debate.core.security.constants import (
    DEFAULT_MAX_UNTRUSTED_LEN,
    INJECTION_PATTERNS,
    MAX_QUERY_LEN,
    MAX_TOPIC_LEN,
    NEUTRALISED_MARKER,
)
from agent_debate.core.security.normalise import normalise_text
from agent_debate.core.security.sanitiser import (
    SecurityGatekeeper,
    sanitize_untrusted_text,
)
from agent_debate.core.security.validation import (
    InvalidInputError,
    SearchQueryInput,
    TopicInput,
    validate_search_query,
    validate_topic,
)

__all__ = [
    "DEFAULT_MAX_UNTRUSTED_LEN",
    "INJECTION_PATTERNS",
    "MAX_QUERY_LEN",
    "MAX_TOPIC_LEN",
    "NEUTRALISED_MARKER",
    "InvalidInputError",
    "SearchQueryInput",
    "SecurityGatekeeper",
    "TopicInput",
    "normalise_text",
    "sanitize_untrusted_text",
    "validate_search_query",
    "validate_topic",
]
