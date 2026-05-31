"""Post-generation word-limit enforcement (TASKS.md 5.7, issue #44).

PRD §5.2 / §7: every debate message must stay within the configured word limit
(``MAX_WORDS``). The **prompt** side already instructs ``<= max_words`` — the
debater system prompt (:mod:`~agent_debate.core.agents.prompts`) and the per-turn
side anchor (:mod:`~agent_debate.core.agents.anchoring`) both state it. This
module is the **verification** half: it is called by the engine (Epic 6) AFTER a
debater generates a turn, and guarantees the message stays within the limit.

Behaviour:

* :func:`count_words` — the single word-counting rule. A "word" is a
  **whitespace-separated token**: ``text.split()`` (so any run of spaces, tabs or
  newlines is one separator and leading/trailing whitespace is ignored). Empty or
  whitespace-only text counts as zero.
* :func:`enforce_word_limit` — verifies the count against ``max_words`` (supplied
  by the caller from :class:`~agent_debate.core.Settings`, never hard-coded). When
  the message is over the limit it is **trimmed to exactly ``max_words`` words** at
  a clean word boundary (the first ``max_words`` tokens are re-joined with single
  spaces) and a violation event is logged; otherwise the text is returned verbatim
  with ``violated=False`` and nothing is logged.

The trim is a clean word-boundary cut (no sentence-boundary heuristic): the first
``max_words`` whitespace tokens, re-joined with single spaces. The violation is
logged as a ``system`` event (the LOG schema has no ``"violation"`` type) carrying
``{"violation": "word_limit", "words": N, "limit": max_words, "trimmed": True}``.

No external/network call is made here (only the LOG sink), so the API gatekeeper
(Epic 13) does not apply. All literals come from
:mod:`agent_debate.core.constants` (single source of truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_debate.core import constants
from agent_debate.log import log_event

#: Separator used when re-joining the kept tokens after a trim (single space).
_TRIM_JOINER = " "

#: ``round`` recorded on the violation event — enforcement is a policy check that
#: is not tied to a specific debate round here (the engine binds the real round).
_VIOLATION_ROUND = 0


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in ``text``.

    The counting rule is ``str.split()`` with no argument: any run of whitespace
    (spaces, tabs, newlines) is a single separator and leading/trailing whitespace
    is ignored, so ``""`` and whitespace-only strings count as zero words.

    Args:
        text: The message text to count.

    Returns:
        The word count (``>= 0``).
    """
    return len(text.split())


@dataclass(frozen=True, slots=True)
class WordLimitResult:
    """Outcome of :func:`enforce_word_limit`.

    Attributes:
        text: The enforced message — unchanged when within the limit, else
            trimmed to exactly ``max_words`` words.
        violated: ``True`` iff the original message exceeded ``max_words``.
        original_words: The word count of the message *before* any trim.
    """

    text: str
    violated: bool
    original_words: int


def enforce_word_limit(
    text: str,
    *,
    max_words: int,
    run_id: str | None = None,
    runs_dir: Path | str | None = None,
    agent: str = constants.WORD_LIMIT_LOG_AGENT,
    round_: int = _VIOLATION_ROUND,
) -> WordLimitResult:
    """Verify ``text`` against ``max_words``, trimming + logging on a breach.

    If the message holds at most ``max_words`` words it is returned verbatim with
    ``violated=False`` and nothing is logged. If it is over the limit it is trimmed
    to **exactly** ``max_words`` words (a clean word-boundary cut — the first
    ``max_words`` tokens re-joined with single spaces) and, when ``run_id`` is
    given, a ``system`` violation event is logged via the LOG package recording the
    original word count, the limit and ``trimmed=True``.

    Args:
        text: The freshly generated message to enforce.
        max_words: The per-message word limit, from
            :class:`~agent_debate.core.Settings` (never hard-coded).
        run_id: When set, a violation event is logged on a breach (else skipped).
        runs_dir: Optional run-log directory passed through to the LOG package.
        agent: Label recorded on the violation event (defaults to the named
            :data:`~agent_debate.core.constants.WORD_LIMIT_LOG_AGENT`).
        round_: Round recorded on the violation event (the engine may pass the
            real debate round).

    Returns:
        A :class:`WordLimitResult` with the enforced text and violation flag.
    """
    words = text.split()
    count = len(words)
    if count <= max_words:
        return WordLimitResult(text=text, violated=False, original_words=count)
    trimmed = _TRIM_JOINER.join(words[:max_words])
    if run_id is not None:
        _log_violation(count, max_words, run_id, runs_dir, agent, round_)
    return WordLimitResult(text=trimmed, violated=True, original_words=count)


def _log_violation(
    words: int,
    limit: int,
    run_id: str,
    runs_dir: Path | str | None,
    agent: str,
    round_: int,
) -> None:
    """Emit one ``system`` event describing the word-limit breach (observability)."""
    payload: dict[str, object] = {
        "violation": constants.WORD_LIMIT_VIOLATION_TAG,
        "words": words,
        "limit": limit,
        "trimmed": True,
    }
    kwargs = {"runs_dir": runs_dir} if runs_dir is not None else {}
    log_event(
        run_id=run_id,
        agent=agent,
        event_type=constants.WORD_LIMIT_LOG_EVENT_TYPE,
        round=round_,
        payload=payload,
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = ["WordLimitResult", "count_words", "enforce_word_limit"]
