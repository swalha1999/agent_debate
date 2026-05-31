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
each ≤ ``config.max_words``. After the main rounds — and before the verdict — a
freer **closing discussion** runs (task 6.5, :mod:`~agent_debate.core.engine.
closing`), its turns stored in ``DebateResult.closing_discussion`` (separate from
the main transcript). After it, the controller renders the final **verdict** (task
8.3, :func:`~agent_debate.core.skills.render_verdict`) — a debate-derived summary +
converged flag + result + winner + reasoning, judged on argumentation/rebuttal/
engagement (NOT factual correctness, PRD §3) — set on ``DebateResult.verdict`` and
logged as a ``verdict`` event. EVERY model call routes through the API gatekeeper
(Epic 13); the per-turn helper (:mod:`turn`) marks the seam where 6.4's timeout/
retry slots in. Caps come from ``config`` (no hard-coding); every message / nudge /
verdict is logged via the LOG package.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.engine._cost import price_result
from agent_debate.core.engine._verdict import render_loop_verdict
from agent_debate.core.engine.closing import run_closing_discussion
from agent_debate.core.engine.drift import run_drift_check
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import CostTotals, DebateMessage, DebateResult
from agent_debate.core.engine.setup import DebateSetup
from agent_debate.core.engine.stream import EventSink
from agent_debate.core.engine.turn import run_debate_turn
from agent_debate.core.gatekeeper import ApiGatekeeper, load_rate_limit_config
from agent_debate.core.pricing import PriceTable
from agent_debate.core.skills import DebateSide, NudgeMessage
from agent_debate.log import DEFAULT_RUNS_DIR


def run_debate_loop(
    setup: DebateSetup,
    config: DebateConfig,
    *,
    gatekeeper: Gatekeeper | None = None,
    run_id: str,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
    sink: EventSink | None = None,
    price_table: PriceTable | None = None,
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
        sink: An optional :class:`~agent_debate.core.engine.stream.EventSink` that
            receives every emitted event live, in order, as it happens (§6, task
            6.6). ``None`` (the default) keeps the log-only behaviour unchanged.
        price_table: Per-model price table used to price the run's cost-breakdown
            (PRD §10/§11); when ``None`` the config-driven ``config/model_prices.
            json`` is loaded. Injected in tests to pin costs to known prices.

    Returns:
        The assembled :class:`DebateResult` (transcript + nudges + closing
        discussion + the debate-derived verdict + totals).
    """
    keeper = gatekeeper or ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)
    transcript: list[DebateMessage] = []
    nudges: list[NudgeMessage] = []
    last_pro: str | None = None
    last_con: str | None = None
    for round_ in range(1, config.rounds + 1):
        last_pro = _turn(
            setup,
            config,
            keeper,
            run_id,
            runs_dir,
            DebateSide.PRO,
            round_,
            last_con,
            transcript,
            sink,
        )
        _drift(setup, transcript[-1], DebateSide.PRO, round_, run_id, runs_dir, nudges, sink)
        last_con = _turn(
            setup,
            config,
            keeper,
            run_id,
            runs_dir,
            DebateSide.CON,
            round_,
            last_pro,
            transcript,
            sink,
        )
        _drift(setup, transcript[-1], DebateSide.CON, round_, run_id, runs_dir, nudges, sink)
    closing = run_closing_discussion(
        setup, config, gatekeeper=keeper, run_id=run_id, runs_dir=runs_dir, sink=sink
    )
    result = DebateResult(
        topic=setup.topic,
        transcript=transcript,
        nudges=nudges,
        closing_discussion=closing,
        verdict=render_loop_verdict(transcript + closing, run_id, runs_dir, sink),
        totals=CostTotals.from_messages(transcript + closing),
    )
    return price_result(result, config, price_table)


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
    sink: EventSink | None,
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
        sink=sink,
    )
    transcript.append(message)
    return None if message.failed else message.content


def _drift(  # noqa: PLR0913 — explicit per-check dependencies (no shared mutable state).
    setup: DebateSetup,
    message: DebateMessage,
    side: DebateSide,
    round_: int,
    run_id: str,
    runs_dir: Path | str,
    nudges: list[NudgeMessage],
    sink: EventSink | None,
) -> None:
    """Drift-check ``message``; on capture inject the private nudge + record it.

    The correction is injected into the captured agent's OWN context (anti-sycophancy
    §4) — never the opponent's, never the public transcript — so it reads the moderator
    note before its next turn. The nudge is logged + streamed but is **not** a debate
    turn (the 10-vs-10 message invariant is unaffected).
    """
    correction = run_drift_check(
        message=message.content,
        side=side,
        round_=round_,
        run_id=run_id,
        runs_dir=runs_dir,
        context=setup.contexts.for_side(side),
        sink=sink,
    )
    if correction is not None:
        nudges.append(correction)


__all__ = ["run_debate_loop"]
