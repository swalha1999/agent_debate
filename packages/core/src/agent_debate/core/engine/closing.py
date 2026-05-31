"""Closing discussion phase — a freer exchange before judgement (issue #50, §3.3).

Orchestration sub-PRD §3.3: after the main ``rounds``-round loop and *before* the
verdict, the debate runs a **closing discussion** — "a freer exchange before
judgement". Each debater (Pro then Con) gives one closing statement per exchange;
the number of exchanges is the single named :data:`~agent_debate.core.constants.
CLOSING_EXCHANGES` constant (no inline magic number).

"Freer" framing. Unlike a main-loop turn — which injects the strict adversarial
relay of the opponent's latest message ("…«…». Rebut it.") — a closing turn injects
a less-constrained :data:`~agent_debate.core.constants.CLOSING_PROMPT_LINE`: the
debater responds *freely* to the other side and makes its strongest final case. It
is STILL side-anchored (stays FOR/AGAINST) and STILL word-limited.

Reuses the main turn machinery so nothing is bypassed: the model call routes
through the API gatekeeper under the 6.4 timeout + retry wrapper
(:func:`~agent_debate.core.engine._call.generate_turn_output`), the word limit is
enforced post-generation (:func:`~agent_debate.core.agents.enforce_word_limit`),
and each turn is logged as a ``message`` event tagged ``closing`` with the
:data:`~agent_debate.core.constants.CLOSING_ROUND` (``0``) marker so it is
distinguishable from the numbered main loop. The returned turns are stored in
:attr:`~agent_debate.core.engine.result.DebateResult.closing_discussion`, kept
separate from the main ``transcript``. All literals come from
:mod:`agent_debate.core.constants`; ``max_words`` comes from the
:class:`~agent_debate.core.engine.models.DebateConfig` (never hard-coded).
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.agents import enforce_word_limit
from agent_debate.core.agents.context import AgentContext
from agent_debate.core.agents.prompts import SIDE_LABEL
from agent_debate.core.engine._call import TurnFailedError, generate_turn_output
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import DebateMessage
from agent_debate.core.engine.setup import DebateSetup
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide


def run_closing_discussion(
    setup: DebateSetup,
    config: DebateConfig,
    *,
    gatekeeper: Gatekeeper,
    run_id: str,
    runs_dir: Path | str,
    sink: EventSink | None = None,
) -> list[DebateMessage]:
    """Run the freer closing exchange after the main loop, before judgement (§3.3).

    Runs :data:`~agent_debate.core.constants.CLOSING_EXCHANGES` exchanges; each
    exchange is one closing statement from Pro then Con. Every closing model call
    routes through ``gatekeeper`` (no bypass), is word-limited and logged as a
    ``closing``-tagged ``message`` event.

    Args:
        setup: The prepared run state (agents + isolated contexts).
        config: The run config (supplies ``max_words``; never hard-coded).
        gatekeeper: The API gatekeeper every model call routes through (Epic 13).
        run_id: The run id stamped on every emitted event.
        runs_dir: Directory holding the per-run JSONL sink.
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The ordered closing turns (Pro then Con, per exchange).
    """
    closing: list[DebateMessage] = []
    for _ in range(constants.CLOSING_EXCHANGES):
        for side in (DebateSide.PRO, DebateSide.CON):
            message = _closing_turn(setup, config, gatekeeper, run_id, runs_dir, side, sink)
            if message is not None:
                closing.append(message)
    return closing


def _closing_turn(  # noqa: PLR0913 — explicit per-turn deps (no shared mutable state).
    setup: DebateSetup,
    config: DebateConfig,
    gatekeeper: Gatekeeper,
    run_id: str,
    runs_dir: Path | str,
    side: DebateSide,
    sink: EventSink | None,
) -> DebateMessage | None:
    """Run one freer closing statement for ``side`` (gatekept, word-limited, logged).

    A FAILED model call (timeout + retry budget exhausted) is skipped (``None``) so
    the closing phase degrades gracefully — it produces no closing turn rather than
    crashing the run (§4).
    """
    agent = setup.pro_agent if side is DebateSide.PRO else setup.con_agent
    context = setup.contexts.for_side(side)
    _inject_closing_prompt(context, side, config)
    try:
        output = generate_turn_output(
            gatekeeper,
            agent.run_sync,
            message_history=context.message_history(),
            service=constants.LOOP_MODEL_SERVICE,
            config=config,
            run_id=run_id,
            round_=constants.CLOSING_ROUND,
            agent=side.value,
            runs_dir=runs_dir,
            sink=sink,
        )
    except TurnFailedError:
        return None
    enforced = enforce_word_limit(
        output.output,
        max_words=config.max_words,
        run_id=run_id,
        runs_dir=runs_dir,
        agent=side.value,
        round_=constants.CLOSING_ROUND,
        sink=sink,
    )
    context.append_assistant(enforced.text)
    return _record_closing(side, enforced.text, run_id, runs_dir, sink)


def _inject_closing_prompt(context: AgentContext, side: DebateSide, config: DebateConfig) -> None:
    """Inject the freer closing prompt (side-anchored, word-limited) as a user turn."""
    prompt = constants.CLOSING_PROMPT_LINE.format(label=SIDE_LABEL[side])
    limit = constants.CLOSING_WORD_LIMIT_LINE.format(max_words=config.max_words)
    context.append_user(f"{prompt} {limit}")


def _record_closing(
    side: DebateSide, content: str, run_id: str, runs_dir: Path | str, sink: EventSink | None
) -> DebateMessage:
    """Build the closing :class:`DebateMessage`, logging + streaming a tagged event."""
    message = DebateMessage(round=constants.CLOSING_ROUND + 1, side=side, content=content)
    emit_event(
        sink,
        run_id=run_id,
        agent=side.value,
        event_type=constants.LOOP_MESSAGE_EVENT_TYPE,
        round=constants.CLOSING_ROUND,
        payload={
            "content": content,
            "word_count": message.word_count,
            constants.CLOSING_MESSAGE_TAG: True,
        },
        runs_dir=runs_dir,
    )
    return message


__all__ = ["run_closing_discussion"]
