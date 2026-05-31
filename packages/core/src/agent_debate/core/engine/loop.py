"""Main 10-vs-10 debate loop — orchestration §3.2 (issue #48, task 6.3).

Drives the debate between the Pro and Con agents prepared by
:func:`~agent_debate.core.setup_debate`, moderated by the Controller's drift-check,
into a :class:`DebateResult`. For ``round = 1..config.rounds`` (default 10) it runs,
in order:

1. **Pro turn** — inject the side anchor (and, from round 2+, the adversarial relay
   of Con's last message) into Pro's OWN context, generate via the gatekeeper,
   enforce the word limit, append + log a ``message`` event.
2. **Controller drift-check on Pro** — :func:`~agent_debate.core.engine.drift.
   run_drift_check`; on capture record a nudge (NOT a debate turn) + log it.
3. **Con turn** — inject the anchor + the adversarial relay of Pro's *latest*
   message (Con MUST rebut Pro), generate, enforce, append + log.
4. **Controller drift-check on Con** — as for Pro.

Result: exactly ``config.rounds`` Pro + ``config.rounds`` Con messages, alternating,
each ≤ ``config.max_words``. The verdict + closing discussion are 6.4/6.5/6.8 — left
as seams (``verdict=None``, ``closing_discussion=[]``). EVERY debater model call
routes through the API gatekeeper (Epic 13); the per-turn helper (:mod:`turn`) marks
the seam where 6.4's timeout/retry slots in. Caps come from ``config`` (no
hard-coding); every message / nudge is logged via the LOG package.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.engine.drift import run_drift_check
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import CostTotals, DebateMessage, DebateResult
from agent_debate.core.engine.setup import DebateSetup
from agent_debate.core.engine.turn import run_debate_turn
from agent_debate.core.gatekeeper import ApiGatekeeper, load_rate_limit_config
from agent_debate.core.skills import DebateSide, NudgeMessage
from agent_debate.log import DEFAULT_RUNS_DIR


def run_debate_loop(
    setup: DebateSetup,
    config: DebateConfig,
    *,
    gatekeeper: Gatekeeper | None = None,
    run_id: str,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> DebateResult:
    """Run the ``config.rounds``-round Pro/Con loop into a :class:`DebateResult` (§3.2).

    Alternates Pro turn → controller drift-check → Con turn → controller drift-check
    for each round, producing exactly ``config.rounds`` Pro + ``config.rounds`` Con
    messages (each ≤ ``config.max_words``) and logging every message / nudge. When no
    ``gatekeeper`` is injected a default :class:`ApiGatekeeper` is built from the
    rate-limit config so every model call still routes through the chokepoint.

    Args:
        setup: The prepared run state (agents, isolated contexts, topic, sides).
        config: The run config (``rounds`` and ``max_words`` drive the loop).
        gatekeeper: The API gatekeeper to route model calls through; built from the
            rate-limit config when ``None`` (Epic 13).
        run_id: The run id stamped on every emitted event.
        runs_dir: Directory holding the per-run JSONL sink.

    Returns:
        The assembled :class:`DebateResult` (transcript + nudges + totals); the
        verdict (``None``) and closing discussion (``[]``) are left as 6.4+ seams.
    """
    keeper = gatekeeper or ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)
    transcript: list[DebateMessage] = []
    nudges: list[NudgeMessage] = []
    last_pro: str | None = None
    last_con: str | None = None
    for round_ in range(1, config.rounds + 1):
        last_pro = _turn(
            setup, config, keeper, run_id, runs_dir, DebateSide.PRO, round_, last_con, transcript
        )
        _drift(transcript[-1], DebateSide.PRO, round_, run_id, runs_dir, nudges)
        last_con = _turn(
            setup, config, keeper, run_id, runs_dir, DebateSide.CON, round_, last_pro, transcript
        )
        _drift(transcript[-1], DebateSide.CON, round_, run_id, runs_dir, nudges)
    return DebateResult(
        topic=setup.topic,
        transcript=transcript,
        nudges=nudges,
        totals=CostTotals.from_messages(transcript),
    )


def _turn(  # noqa: PLR0913 — explicit per-turn dependencies (no shared mutable state).
    setup: DebateSetup,
    config: DebateConfig,
    keeper: Gatekeeper,
    run_id: str,
    runs_dir: Path | str,
    side: DebateSide,
    round_: int,
    opponent_message: str | None,
    transcript: list[DebateMessage],
) -> str | None:
    """Run one debater turn, append it to ``transcript`` and return its content.

    A FAILED turn (its model call exhausted the timeout + retry budget) is still
    recorded in the transcript (marked ``failed``) so the run does not crash, but
    returns ``None`` — the opponent gets a fresh anchor rather than being asked to
    rebut a failure marker (the §4 graceful-degradation policy).
    """
    agent = setup.pro_agent if side is DebateSide.PRO else setup.con_agent
    message = run_debate_turn(
        agent=agent,
        context=setup.contexts.for_side(side),
        side=side,
        round_=round_,
        config=config,
        gatekeeper=keeper,
        run_id=run_id,
        runs_dir=runs_dir,
        opponent_message=opponent_message,
    )
    transcript.append(message)
    return None if message.failed else message.content


def _drift(  # noqa: PLR0913 — explicit per-check dependencies (no shared mutable state).
    message: DebateMessage,
    side: DebateSide,
    round_: int,
    run_id: str,
    runs_dir: Path | str,
    nudges: list[NudgeMessage],
) -> None:
    """Drift-check ``message`` and record a nudge when the agent was captured."""
    correction = run_drift_check(
        message=message.content, side=side, round_=round_, run_id=run_id, runs_dir=runs_dir
    )
    if correction is not None:
        nudges.append(correction)


__all__ = ["run_debate_loop"]
