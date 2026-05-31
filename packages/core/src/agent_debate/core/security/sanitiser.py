"""Security sanitisation gatekeeper for untrusted text (PRD §5.7, task 7.1).

All external text — the user-supplied topic, **web-search results** and model
output — must pass through here *before* it re-enters any prompt, so untrusted
content cannot act as an instruction (prompt-injection defence). This is the
**security** gatekeeper, distinct from the API/rate-limit gatekeeper (Epic 13).
It is pure text processing: it makes **no network call** (the ``web_search``
skill, task 4.1, passes its results through this), and every threshold/pattern
comes from :mod:`agent_debate.core.security.constants` (single source of truth).

Strategy (defence-in-depth, documented, not a perfect parser):

1. **Normalise** — NFKC + strip control / zero-width chars + collapse whitespace
   (:func:`agent_debate.core.security.normalise.normalise_text`), so disguised
   keywords reassemble and can be matched.
2. **Neutralise** — redact the common injection phrasings
   (:data:`~constants.INJECTION_PATTERNS`) with
   :data:`~constants.NEUTRALISED_MARKER`, so they read as inert data, not orders.
3. **Length-cap** — truncate to ``max_length``
   (:data:`~constants.DEFAULT_MAX_UNTRUSTED_LEN`, overridable per call) to bound
   the blast radius and token cost of a hostile payload.

When step 2 neutralises anything, an observable ``system`` event is logged via
the LOG package (optional: only when a ``run_id`` is supplied).
"""

from __future__ import annotations

import re
from pathlib import Path

from agent_debate.core.security import constants
from agent_debate.core.security.normalise import normalise_text
from agent_debate.log import log_event

#: Pre-compiled, case-insensitive injection matchers built once from the named
#: pattern list (no inline magic; the patterns live in :mod:`constants`).
_COMPILED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in constants.INJECTION_PATTERNS
)


def _neutralise_injections(text: str) -> tuple[str, int]:
    """Redact known injection phrasings; return ``(text, neutralised_count)``.

    Each pattern match is replaced with :data:`constants.NEUTRALISED_MARKER`, so
    role markers / override phrases survive only as visibly inert data. The count
    drives the optional ``system`` log event (observability) and is otherwise
    ignored by callers.
    """
    count = 0
    result = text
    for pattern in _COMPILED_PATTERNS:
        result, hits = pattern.subn(constants.NEUTRALISED_MARKER, result)
        count += hits
    return result, count


def sanitize_untrusted_text(
    text: str,
    *,
    max_length: int = constants.DEFAULT_MAX_UNTRUSTED_LEN,
    source: str | None = None,
    run_id: str | None = None,
    runs_dir: Path | str | None = None,
) -> str:
    """Return a prompt-safe form of untrusted ``text`` (normalise → neutralise → cap).

    Args:
        text: Untrusted input (user topic, web-search result, model output).
        max_length: Character cap applied last; defaults to
            :data:`constants.DEFAULT_MAX_UNTRUSTED_LEN`. Overridable per call.
        source: Optional label (e.g. ``"web_search"``) recorded on the log event.
        run_id: When set, a ``system`` event is logged if anything was neutralised.
        runs_dir: Optional run-log directory passed through to the LOG package.

    Returns:
        A normalised, injection-neutralised, length-capped ``str`` (never ``None``).
    """
    normalised = normalise_text(text)
    neutralised, count = _neutralise_injections(normalised)
    capped = neutralised[:max_length]
    if count and run_id is not None:
        _log_neutralised(count, source, run_id, runs_dir)
    return capped


def _log_neutralised(
    count: int,
    source: str | None,
    run_id: str,
    runs_dir: Path | str | None,
) -> None:
    """Emit one ``system`` event noting how many injection patterns were redacted."""
    payload: dict[str, object] = {"neutralised": count, "source": source}
    kwargs = {"runs_dir": runs_dir} if runs_dir is not None else {}
    log_event(
        run_id=run_id,
        agent=constants.LOG_AGENT,
        event_type=constants.LOG_EVENT_TYPE,
        round=0,
        payload=payload,
        **kwargs,  # type: ignore[arg-type]
    )


class SecurityGatekeeper:
    """Stateful wrapper binding sanitiser defaults (PRD §5.7).

    Holds the ``max_length`` cap and the optional ``run_id``/``runs_dir`` log
    target once, so callers that sanitise many fragments (e.g. a list of
    web-search snippets) pass only the text. :meth:`sanitize` is a thin,
    side-effect-faithful delegate to :func:`sanitize_untrusted_text`.
    """

    def __init__(
        self,
        *,
        max_length: int = constants.DEFAULT_MAX_UNTRUSTED_LEN,
        run_id: str | None = None,
        runs_dir: Path | str | None = None,
    ) -> None:
        """Bind the ``max_length`` cap and optional ``run_id``/``runs_dir``."""
        self._max_length = max_length
        self._run_id = run_id
        self._runs_dir = runs_dir

    def sanitize(self, text: str, *, source: str | None = None) -> str:
        """Sanitise ``text`` using this gatekeeper's bound defaults."""
        return sanitize_untrusted_text(
            text,
            max_length=self._max_length,
            source=source,
            run_id=self._run_id,
            runs_dir=self._runs_dir,
        )


__all__ = ["SecurityGatekeeper", "sanitize_untrusted_text"]
