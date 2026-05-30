"""Redaction + truncation structlog processor for ``agent_debate.log`` (1.4).

This module is a **runtime** structlog processor that runs in the chain wired by
:func:`agent_debate.log.configure` *before* the renderers, so its effect applies
to **both** sinks from PRD §5.8 (the pretty console renderer and the per-run
JSONL file). It is the runtime counterpart to the build-time
``scripts/secret_scan.py`` gate (PRD §7.4): the scanner stops secrets entering
the repo, this stops them entering the logs.

Two transforms are applied, recursing into nested dicts/lists (e.g. the
:class:`~agent_debate.log.event.LogEvent` payload):

* **Key-based redaction** — a value whose *key* name contains any secret hint
  (:data:`SECRET_KEY_HINTS`, case-insensitive, e.g. ``api_key``/``token``/
  ``password``) is replaced with the :data:`REDACTED` marker.
* **Value-based redaction** — a string matching any secret *value* pattern
  (:data:`SECRET_VALUE_PATTERNS`: ``sk-…``/``sk-ant-…``, AWS ``AKIA…``, PEM
  headers, bearer tokens) is redacted regardless of its key. A partial match
  inside a longer string redacts the whole value (fail-safe).
* **Truncation** — any remaining string longer than :data:`MAX_VALUE_LEN`
  (configurable via :func:`make_redactor`) is cut to that length and suffixed
  with :data:`TRUNCATED_SUFFIX`.

The core is a pure function (:func:`redact_value`) taking and returning plain
data, so it is unit-testable without structlog. :func:`make_redactor` builds a
processor with a custom ``max_len``; :func:`redact_event` is the default-length
processor wired into the chain. No external API calls are made, so the API
gatekeeper (Epic 13) is N/A.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from structlog.typing import EventDict

#: Marker substituted for any redacted secret value.
REDACTED = "***REDACTED***"

#: Suffix appended to a truncated string so readers know it was cut.
TRUNCATED_SUFFIX = "...[truncated]"

#: Default maximum length for a single string value before truncation. Single
#: source of truth (guideline §7.2); override per-processor via
#: :func:`make_redactor`'s ``max_len`` — never a scattered magic number.
MAX_VALUE_LEN = 2048

#: Case-insensitive substrings that mark a *key* as carrying a secret value.
SECRET_KEY_HINTS: tuple[str, ...] = (
    "key",
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "auth",
    "credential",
    "api_key",
    "apikey",
)

#: Exact (case-insensitive) key names that are *never* secrets even though they
#: contain a hint substring — e.g. the :class:`~agent_debate.log.event.LogEvent`
#: ``tokens`` *count* field (contains "token"). Prevents false-positive
#: redaction of legitimate, non-secret metadata.
SAFE_KEYS: frozenset[str] = frozenset({"tokens", "token_count", "tokens_used"})

#: Named secret *value* patterns, aligned with ``scripts/secret_scan.py`` and
#: extended with bearer tokens; any match redacts the whole value (fail-safe).
SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"[Bb]earer\s+[A-Za-z0-9._-]{8,}"),
)


def _key_is_secret(key: str) -> bool:
    """Return ``True`` when ``key`` names a secret (hint match, not allowlisted)."""
    lowered = key.lower()
    if lowered in SAFE_KEYS:
        return False
    return any(hint in lowered for hint in SECRET_KEY_HINTS)


def _value_has_secret(value: str) -> bool:
    """Return ``True`` when ``value`` matches any secret value pattern."""
    return any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS)


def _redact_str(value: str, max_len: int) -> str:
    """Redact a secret-bearing string, else truncate it past ``max_len``."""
    if _value_has_secret(value):
        return REDACTED
    if len(value) > max_len:
        return value[:max_len] + TRUNCATED_SUFFIX
    return value


def redact_value(value: Any, max_len: int = MAX_VALUE_LEN) -> Any:
    """Return ``value`` with secrets redacted and long strings truncated.

    Pure and recursive: dicts are walked (a secret-like *key* redacts its value
    outright; otherwise the value is processed), lists/tuples are mapped, strings
    are redacted-or-truncated, and other scalars pass through unchanged. Taking
    and returning plain data keeps it unit-testable without structlog.

    Args:
        value: Arbitrary JSON-like data (the event dict or a nested member).
        max_len: Length past which a (non-secret) string is truncated.

    Returns:
        A redacted/truncated copy of ``value``.
    """
    if isinstance(value, dict):
        return {
            key: (REDACTED if _key_is_secret(str(key)) else redact_value(member, max_len))
            for key, member in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_value(member, max_len) for member in value]
    if isinstance(value, str):
        return _redact_str(value, max_len)
    return value


def _redact_event_dict(event_dict: EventDict, max_len: int) -> EventDict:
    """Apply :func:`redact_value` to each entry, returning a new event dict."""
    result: dict[str, Any] = {}
    for key, member in dict(event_dict).items():
        result[key] = REDACTED if _key_is_secret(str(key)) else redact_value(member, max_len)
    return result


def make_redactor(max_len: int = MAX_VALUE_LEN) -> Any:
    """Build a structlog processor that redacts/truncates with ``max_len``.

    Args:
        max_len: Length past which non-secret string values are truncated.

    Returns:
        A processor ``(logger, method_name, event_dict) -> event_dict``.
    """

    def _processor(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
        return _redact_event_dict(event_dict, max_len)

    return _processor


def redact_event(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """Default-length redaction processor wired into the configure() chain."""
    return _redact_event_dict(event_dict, MAX_VALUE_LEN)
