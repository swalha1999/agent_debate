"""Deterministic drift detector for ``assess_drift`` (TASKS.md 8.1, issue #60).

Epic 8.1 deepens the 4.4 baseline into a robust, **deterministic** classifier of
the four anti-sycophancy §3 drift signals — concession, framing/conclusion
adoption (agreement), hedging, and restating-the-opponent-without-rebuttal. It
makes no LLM/network call (the controller LLM may still pass explicit ``signals``
to ``assess_drift``), so the API gatekeeper (Epic 13) is N/A here.

Split out of :mod:`agent_debate.core.skills.controller` so that module stays under
the 150-line guideline (split, don't compress). Every phrase set, weight and the
capture threshold are named constants in :mod:`agent_debate.core.constants` — no
literals live here. :func:`detect_drift` returns ``(confidence, labels)``: the
clamped weighted confidence in ``[0, 1]`` and the human-readable labels of the
signals that fired (empty when on-side).
"""

from __future__ import annotations

from agent_debate.core.skills import _drift_constants as c


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Return ``True`` if ``text`` (already lower-cased) contains any of ``phrases``."""
    return any(phrase in text for phrase in phrases)


def _content_tokens(text: str) -> set[str]:
    """Lower-cased alphanumeric tokens longer than the stop-word length cutoff."""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return {token for token in cleaned.split() if len(token) >= c.DRIFT_MIN_OVERLAP_TOKEN_LEN}


def _overlap_ratio(message: str, opponent_message: str) -> float:
    """Fraction of the opponent's content tokens that reappear in ``message``."""
    opponent_tokens = _content_tokens(opponent_message)
    if not opponent_tokens:
        return 0.0
    shared = opponent_tokens & _content_tokens(message)
    return len(shared) / len(opponent_tokens)


def _is_restating(message: str, lowered: str, opponent_message: str | None) -> bool:
    """High overlap with the opponent AND no rebuttal marker => restating it (§3)."""
    if opponent_message is None:
        return False
    if _contains_any(lowered, c.DRIFT_REBUTTAL_MARKERS):
        return False
    return _overlap_ratio(message, opponent_message) >= c.DRIFT_OVERLAP_THRESHOLD


def detect_drift(
    message: str,
    opponent_message: str | None = None,
) -> tuple[float, list[str]]:
    """Score ``message`` for the four §3 drift signals; return ``(confidence, labels)``.

    Each fired signal contributes its named weight to an additive confidence that is
    clamped into ``[0, 1]``; ``labels`` lists the human-readable signal names that
    tripped (empty when the agent looks on-side). ``opponent_message`` is optional
    context used only for the overlap-based restating signal.

    Args:
        message: The agent's latest message text.
        opponent_message: The opponent's last message, for overlap detection.

    Returns:
        The clamped weighted confidence and the list of fired signal labels.
    """
    lowered = message.lower()
    fired: list[tuple[float, str]] = []
    if _contains_any(lowered, c.DRIFT_CONCEDE_PHRASES):
        fired.append((c.DRIFT_WEIGHT_CONCEDE, c.DRIFT_SIGNAL_LABEL_CONCEDE))
    if _contains_any(lowered, c.DRIFT_AGREEMENT_PHRASES):
        fired.append((c.DRIFT_WEIGHT_AGREEMENT, c.DRIFT_SIGNAL_LABEL_AGREEMENT))
    if _contains_any(lowered, c.DRIFT_HEDGE_PHRASES):
        fired.append((c.DRIFT_WEIGHT_HEDGE, c.DRIFT_SIGNAL_LABEL_HEDGE))
    if _is_restating(message, lowered, opponent_message):
        fired.append((c.DRIFT_WEIGHT_RESTATING, c.DRIFT_SIGNAL_LABEL_RESTATING))
    confidence = min(1.0, sum(weight for weight, _ in fired))
    return confidence, [label for _, label in fired]


__all__ = ["detect_drift"]
