"""Final-verdict rendering + logging for the debate loop (split from ``loop.py``).

Extracted so :mod:`loop.py` stays under the 150-line cap (split, don't compress).
After the closing discussion the controller renders the debate-DERIVED verdict and
the loop logs + streams it; this module owns that self-contained concern.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.engine.result import DebateMessage
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide, TranscriptTurn, Verdict, render_verdict


def render_loop_verdict(
    messages: list[DebateMessage],
    run_id: str,
    runs_dir: Path | str,
    sink: EventSink | None,
) -> Verdict | None:
    """Render the final verdict from the debate transcript, log + stream it (§3.2).

    The controller renders a debate-DERIVED verdict (:func:`~agent_debate.core.
    skills.render_verdict`): a summary, whether the agents converged/agreed, the
    result and WHO WON with reasoning — judged on argumentation/rebuttal/engagement,
    never factual correctness (PRD §3). Failed turns (markers, not real arguments)
    are excluded; an all-failed run yields no verdict (``None``). The verdict is
    logged + streamed as a ``verdict`` event so live consumers render it.
    """
    turns = [TranscriptTurn(side=m.side, text=m.content) for m in messages if not m.failed]
    if not turns:
        return None
    verdict = render_verdict(turns)
    label = verdict.winner
    emit_event(
        sink,
        run_id=run_id,
        agent=constants.LOOP_VERDICT_LOG_AGENT,
        event_type=constants.LOOP_VERDICT_EVENT_TYPE,
        round=constants.CLOSING_ROUND,
        payload={
            "winner": label.value if isinstance(label, DebateSide) else label,
            "converged": verdict.converged,
            "summary": verdict.summary,
            "rationale": verdict.rationale,
        },
        runs_dir=runs_dir,
    )
    return verdict


__all__ = ["render_loop_verdict"]
