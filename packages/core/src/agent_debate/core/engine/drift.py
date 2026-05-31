"""Controller drift-check after a turn — assess → nudge (issue #48, §3.2 / §4).

Orchestration sub-PRD §3.2: after each debater turn the controller classifies the
message for *drift* (capture by the opponent) and, when captured, privately
*nudges* the agent back onto its side. Per anti-sycophancy §4 the nudge is logged
and surfaced but **does not** count as a debate turn (``is_debate_turn is False``).

This module is the **drift-check helper** the loop calls for both sides, kept
separate so the loop file stays small (split, not compress). It reuses the
controller skills (:func:`~agent_debate.core.assess_drift` /
:func:`~agent_debate.core.nudge`) — no model call is made here (the baseline
drift detector is deterministic), so the API gatekeeper does not apply to it.

On capture it returns the :class:`NudgeMessage` and logs one ``nudge`` event
(run_id / round / agent); when the message is on-side it returns ``None`` and logs
nothing. Labels come from :mod:`agent_debate.core.constants`.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide, NudgeMessage, assess_drift, nudge


def run_drift_check(
    *,
    message: str,
    side: DebateSide,
    round_: int,
    run_id: str,
    runs_dir: Path | str,
    sink: EventSink | None = None,
) -> NudgeMessage | None:
    """Drift-check ``message`` for ``side``; nudge + log on capture, else ``None``.

    Runs :func:`assess_drift`; if the agent is captured a :func:`nudge` is built,
    logged as a ``nudge`` event (which is **not** a debate turn) and returned.
    A clean (on-side) message returns ``None`` and logs nothing.

    Args:
        message: The debater's just-produced message text.
        side: The debater's assigned stance (drives the nudge target).
        round_: The 1-based round the checked turn belongs to.
        run_id: The run id stamped on the nudge event.
        runs_dir: Directory holding the per-run JSONL sink.
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The :class:`NudgeMessage` when the agent drifted, else ``None``.
    """
    assessment = assess_drift(message, side)
    if not assessment.captured:
        return None
    correction = nudge(side, assessment.reason)
    emit_event(
        sink,
        run_id=run_id,
        agent=constants.LOOP_NUDGE_LOG_AGENT,
        event_type=constants.LOOP_NUDGE_EVENT_TYPE,
        round=round_,
        payload={
            "target": correction.target.value,
            "reason": correction.reason,
            "correction": correction.correction,
            "confidence": assessment.confidence,
        },
        runs_dir=runs_dir,
    )
    return correction


__all__ = ["run_drift_check"]
