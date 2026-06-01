"""Controller message FORWARDING — the father is the relay hub (issue #219, §8.3.7).

HW2 requirements §8.3.7: the debate must flow **through the father** — every message
goes child → father → child; the debaters never communicate directly. This module
makes that routing explicit: when a debater produces a message the loop hands it to
the CONTROLLER ("father"), and :func:`forward_to_opponent` is the controller-owned
step that FORWARDS it (as the §5.6 adversarially-framed relay) into the opponent's
context. The engine no longer relays directly between the two children.

Isolation + framing are preserved exactly. Each hop is wrapped in a structured JSON
:class:`~agent_debate.core.engine.message.AgentMessage` envelope (HW2 §8.3.8 —
inter-agent IPC is monitorable structured JSON); the legible §5.6 relay the model
sees is RENDERED from the envelope via :func:`~agent_debate.core.agents.
build_adversarial_relay` (the single source of the "«…». Rebut it." framing — never
duplicated). So the opponent receives a FRAMED, sanitised message as a ``user`` turn
in its OWN :class:`~agent_debate.core.agents.context.AgentContext` (5.4 isolation);
it never sees the opponent's raw turn and the two debaters never share a thread.
Anti-sycophancy (side anchoring + the adversarial frame) is unchanged.

Routing is observable: each forward logs one ``system`` event tagged
:data:`~agent_debate.core.constants.LOOP_RELAY_EVENT_TAG` carrying the ``from``/``to``
sides, the round, and the structured JSON envelope (under
:data:`~agent_debate.core.constants.LOOP_RELAY_ENVELOPE_KEY`) — the demonstrable
evidence that the message passed through the father (the acceptance criterion). No
model/network call is made here (the framing is pure text processing), so the API
gatekeeper (Epic 13) does not apply.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.engine.message import AgentMessage
from agent_debate.core.engine.stream import EventSink, emit_event
from agent_debate.core.skills import DebateSide


def forward_to_opponent(
    *,
    message: str,
    from_side: DebateSide,
    to_side: DebateSide,
    round_: int,
    run_id: str,
    runs_dir: Path | str,
    sink: EventSink | None = None,
) -> str:
    """Forward ``message`` from ``from_side`` to ``to_side`` THROUGH the controller (§8.3.7).

    The controller (the father) is the relay hub: it frames ``message`` adversarially
    via :func:`~agent_debate.core.agents.build_adversarial_relay` (reused — sanitised +
    "«…». Rebut it.", never re-implemented) and logs one ``system`` routing event so the
    child → father → child flow is demonstrable. The framed text is returned for the
    loop to inject into the opponent's OWN context (5.4 isolation preserved — the
    opponent never receives ``from_side``'s raw turn, only the controller-forwarded
    frame).

    Args:
        message: The debater's just-produced (untrusted) message to forward.
        from_side: The side that produced ``message`` (the sender child).
        to_side: The opponent side the controller forwards it to (the receiver child).
        round_: The 1-based round the forwarded message belongs to.
        run_id: The run id stamped on the routing event.
        runs_dir: Directory holding the per-run JSONL sink.
        sink: Optional live event sink (§6, task 6.6); ``None`` logs only.

    Returns:
        The adversarially framed, sanitised relay text the controller forwards.
    """
    envelope = AgentMessage(round=round_, from_side=from_side, to_side=to_side, content=message)
    framed = envelope.render(run_id=run_id)
    emit_event(
        sink,
        run_id=run_id,
        agent=constants.LOOP_RELAY_LOG_AGENT,
        event_type=constants.LOOP_RELAY_EVENT_TYPE,
        round=round_,
        payload={
            "event": constants.LOOP_RELAY_EVENT_TAG,
            "from": from_side.value,
            "to": to_side.value,
            constants.LOOP_RELAY_ENVELOPE_KEY: envelope.to_payload(),
        },
        runs_dir=runs_dir,
    )
    return framed


__all__ = ["AgentMessage", "forward_to_opponent"]
