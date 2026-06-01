"""Single debater turn — generate → enforce word limit → log (issue #48, §3.2).

Orchestration sub-PRD §3.2: each round runs a Pro turn and a Con turn. This
module is the **one-turn helper** the loop (:mod:`agent_debate.core.engine.loop`)
calls for both sides, kept here so the loop file stays small (split, not compress).

A turn:

1. **Injects** the per-turn side anchor and — once the controller has forwarded the
   opponent's latest message (§8.3.7 child → father → child, see
   :func:`~agent_debate.core.engine.forward.forward_to_opponent`) — that already-framed,
   sanitised adversarial relay into the debater's OWN context (folded into one user
   turn via :func:`~agent_debate.core.agents.anchor_turn`); the opponent must be
   rebutted, never echoed (anti-sycophancy §2).
2. **Generates** the reply by routing ``agent.run_sync`` through the API gatekeeper
   (Epic 13) — EVERY model call passes through :meth:`Gatekeeper.execute`. The
   timeout + retry wrapping is task 6.4; this is the clean seam where it slots in.
3. **Enforces** the word limit post-generation (:func:`~agent_debate.core.agents.
   enforce_word_limit` — trims + logs a violation, config-driven ``max_words``).
4. **Appends** the enforced reply to the debater's context (assistant turn) and
   **logs** one ``message`` event (run_id / round / agent) via the LOG package.

All labels come from :mod:`agent_debate.core.constants`; ``max_words`` comes from
the :class:`DebateConfig`. The function returns the typed :class:`DebateMessage`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.agents import anchor_turn, enforce_word_limit
from agent_debate.core.agents.context import AgentContext
from agent_debate.core.engine._call import TimeoutRunner, TurnFailedError, generate_turn_output
from agent_debate.core.engine._usage import call_tokens
from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import DebateMessage
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide
from pydantic_ai import Agent


def run_debate_turn(
    *,
    agent: Agent[None, str],
    context: AgentContext,
    side: DebateSide,
    round_: int,
    config: DebateConfig,
    gatekeeper: Gatekeeper,
    run_id: str,
    runs_dir: Path | str,
    framed_opponent_message: str | None,
    sleep_fn: Callable[[float], None] = time.sleep,
    timeout_runner: TimeoutRunner | None = None,
    sink: EventSink | None = None,
) -> DebateMessage:
    """Run one debater turn for ``side`` and return its :class:`DebateMessage` (§3.2).

    Injects the side anchor (and, when ``framed_opponent_message`` is given, the
    already-framed adversarial relay the CONTROLLER forwarded — see
    :func:`~agent_debate.core.engine.forward.forward_to_opponent` — so the debater
    rebuts rather than echoes), generates the reply via the gatekeeper, enforces
    ``config.max_words`` (trim + log), then appends the enforced text to ``context``
    and logs one ``message`` event.

    Args:
        agent: The debater agent (built on an injected model in tests).
        context: The debater's OWN isolated context to inject into / append to.
        side: The debater's assigned stance (``PRO``/``CON``).
        round_: The 1-based debate round this turn belongs to.
        config: The run config (supplies ``max_words``, never hard-coded).
        gatekeeper: The API gatekeeper every model call routes through (Epic 13).
        run_id: The run id stamped on every emitted event.
        runs_dir: Directory holding the per-run JSONL sink.
        framed_opponent_message: The opponent's latest message ALREADY framed +
            forwarded by the controller (§8.3.7), or ``None`` on the very first turn
            (no opponent has spoken yet). The debater never sees the raw turn —
            only this controller-forwarded frame.
        sleep_fn: Sleep primitive used between retries; injectable so tests can
            run without real delays (defaults to :func:`time.sleep`).
        timeout_runner: Optional injected timeout+retry runner (task 6.4);
            ``None`` uses the default wrapper.
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The enforced, word-limited :class:`DebateMessage` for the turn.
    """
    _inject_prompt(context, side, config, framed_opponent_message)
    start = time.monotonic()
    # The anchor/relay was just appended as the trailing ``user`` turn, so the
    # whole context history is the run input (its last turn is the live prompt).
    # The model call routes through the gatekeeper under the 6.4 timeout + retry
    # wrapper; on an exhausted budget the turn is marked FAILED (not a crash).
    runner_kw = {} if timeout_runner is None else {"timeout_runner": timeout_runner}
    try:
        output = generate_turn_output(
            gatekeeper,
            agent.run_sync,
            message_history=context.message_history(),
            service=constants.LOOP_MODEL_SERVICE,
            config=config,
            run_id=run_id,
            round_=round_,
            agent=side.value,
            runs_dir=runs_dir,
            sleep_fn=sleep_fn,
            sink=sink,
            **runner_kw,
        )
    except TurnFailedError:
        return _failed_turn(side, round_, run_id, runs_dir)
    latency_ms = (time.monotonic() - start) * 1000.0
    if output is None:  # pragma: no cover — synchronous loop never queues a call.
        msg = "gatekeeper returned no result (call was queued); the loop runs calls inline"
        raise RuntimeError(msg)
    enforced = enforce_word_limit(
        output.output,
        max_words=config.max_words,
        run_id=run_id,
        runs_dir=runs_dir,
        agent=side.value,
        round_=round_,
        sink=sink,
    )
    context.append_assistant(enforced.text)
    return _record(side, round_, enforced.text, output, latency_ms, run_id, runs_dir, sink)


def _failed_turn(side: DebateSide, round_: int, run_id: str, runs_dir: Path | str) -> DebateMessage:
    """Build the FAILED-turn marker after the model call exhausted its budget (§4).

    The controller was already informed via a ``system`` event inside the wrapper
    (:func:`~agent_debate.core.engine._call.generate_turn_output`); here we return
    a ``failed`` :class:`DebateMessage` marker so the loop records the turn and
    continues without crashing. The marker is *not* appended to the opponent's
    context — a failed turn produces no argument to rebut.
    """
    return DebateMessage(
        round=round_, side=side, content=constants.TURN_FAILED_CONTENT, failed=True
    )


def _inject_prompt(
    context: AgentContext,
    side: DebateSide,
    config: DebateConfig,
    framed_opponent_message: str | None,
) -> None:
    """Inject the side anchor, folding in the controller-forwarded frame when present.

    ``framed_opponent_message`` is the already-sanitised, already-adversarially-framed
    relay the controller forwarded (§8.3.7) — it is folded into the SAME ``user`` turn
    as the side anchor (via :func:`~agent_debate.core.agents.anchor_turn`), never
    re-framed here. Only ``context`` (the debater's OWN history) is mutated, so 5.4
    isolation holds.
    """
    anchor_turn(context, side, max_words=config.max_words, opponent_message=framed_opponent_message)


def _record(  # noqa: PLR0913 — explicit per-record deps (no shared mutable state).
    side: DebateSide,
    round_: int,
    content: str,
    output: object,
    latency_ms: float,
    run_id: str,
    runs_dir: Path | str,
    sink: EventSink | None,
) -> DebateMessage:
    """Build the :class:`DebateMessage`, logging + streaming one ``message`` event."""
    input_tokens, output_tokens = call_tokens(output)
    message = DebateMessage(
        round=round_,
        side=side,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
    emit_event(
        sink,
        run_id=run_id,
        agent=side.value,
        event_type=constants.LOOP_MESSAGE_EVENT_TYPE,
        round=round_,
        payload={"content": content, "word_count": message.word_count},
        tokens=input_tokens + output_tokens,
        latency_ms=latency_ms,
        runs_dir=runs_dir,
    )
    return message


__all__ = ["run_debate_turn"]
