"""Controller drift-check after a turn — assess → nudge (issue #48/#61, §3.2 / §4).

Orchestration sub-PRD §3.2 / anti-sycophancy §2.4–§4: after each debater turn the
controller classifies the message for *drift* (capture by the opponent) and, when
captured, sends a PRIVATE correction to **that** agent. Per §4 the nudge is logged
and surfaced (the 6.6 event stream) but **does not** count as a debate turn
(``is_debate_turn is False``) — the 10-vs-10 message invariant is unaffected.

This module is the **drift-check helper** the loop calls for both sides, kept
separate so the loop file stays small (split, not compress). It reuses the
controller skills (:func:`~agent_debate.core.assess_drift` /
:func:`~agent_debate.core.nudge`) — no model call is made here (the baseline
drift detector is deterministic), so the API gatekeeper does not apply to it.

"Private" means the correction is injected into the captured agent's OWN
:class:`~agent_debate.core.agents.context.AgentContext` (so it sees the note on
its next turn and can course-correct) — never the opponent's context and never the
public transcript. On capture :func:`run_drift_check` builds + injects the
correction, logs one ``nudge`` event (run_id / round / agent) and returns the
:class:`NudgeMessage`; an on-side message returns ``None`` and logs nothing. Labels
come from :mod:`agent_debate.core.constants`.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.agents.context import AgentContext
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide, NudgeMessage, assess_drift, nudge


def inject_nudge(context: AgentContext, correction: NudgeMessage) -> str:
    """Inject a private ``correction`` into the captured agent's OWN ``context``.

    Appends the correction text as a ``user`` turn in the agent's isolated history
    (anti-sycophancy §4) so the agent reads the private moderator note before its
    next turn. The opponent's context and the public transcript are never touched,
    and the nudge is **not** a debate turn (``correction.is_debate_turn is False``).

    Args:
        context: The captured agent's own :class:`AgentContext` to append into.
        correction: The :class:`NudgeMessage` whose correction text is injected.

    Returns:
        The exact correction text appended to ``context``.
    """
    context.append_user(correction.correction)
    return correction.correction


def run_drift_check(
    *,
    message: str,
    side: DebateSide,
    round_: int,
    run_id: str,
    runs_dir: Path | str,
    context: AgentContext | None = None,
    sink: EventSink | None = None,
) -> NudgeMessage | None:
    """Drift-check ``message`` for ``side``; nudge + log on capture, else ``None``.

    Runs :func:`assess_drift`; if the agent is captured a :func:`nudge` is built,
    its private correction injected into the captured agent's ``context`` (when
    supplied) via :func:`inject_nudge`, logged as a ``nudge`` event (which is **not**
    a debate turn) and returned. A clean (on-side) message returns ``None``, injects
    nothing and logs nothing.

    Args:
        message: The debater's just-produced message text.
        side: The debater's assigned stance (drives the nudge target).
        round_: The 1-based round the checked turn belongs to.
        run_id: The run id stamped on the nudge event.
        runs_dir: Directory holding the per-run JSONL sink.
        context: The captured agent's OWN context; the private correction is
            injected into it when supplied (``None`` skips injection, log only).
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The :class:`NudgeMessage` when the agent drifted, else ``None``.
    """
    assessment = assess_drift(message, side)
    if not assessment.captured:
        return None
    correction = nudge(side, assessment.reason)
    if context is not None:
        inject_nudge(context, correction)
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


__all__ = ["inject_nudge", "run_drift_check"]
