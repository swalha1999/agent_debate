"""Structured JSON inter-agent message envelope (issue #220, HW2 §8.3.8).

HW2 requirements §8.3.8: inter-agent / IPC communication should use a structured
**JSON** format — monitorable and token-saving. The agent-to-agent hop in this
system is the controller's forward step (:func:`~agent_debate.core.engine.forward.
forward_to_opponent`, the §8.3.7 child → father → child relay). This module gives
that hop a typed envelope, :class:`AgentMessage`, used as the **transport + logged
representation** of every forwarded turn.

The envelope is pure structured data: ``round`` / ``from_side`` / ``to_side`` /
``type`` / ``content`` (the raw debater text). It is JSON-serialisable
(:meth:`~pydantic.BaseModel.model_dump_json`) and round-trips losslessly, so the
run log carries a monitorable structured record of every inter-agent hop.

Crucially the envelope does **not** change what the model sees: :meth:`AgentMessage.
render` delegates to :func:`~agent_debate.core.agents.build_adversarial_relay` (the
single source of the §5.6 "Your opponent argued: «…». Rebut it." framing) on
``content`` — so the debater still receives the legible adversarial prompt and
debate quality / anti-sycophancy are untouched. Envelope = structured JSON
transport; render = legible text injected into the opponent's context.
"""

from __future__ import annotations

from agent_debate.core import constants
from agent_debate.core.agents.relay import build_adversarial_relay
from agent_debate.core.skills import DebateSide
from pydantic import BaseModel, ConfigDict


class AgentMessage(BaseModel):
    """A structured JSON envelope for one inter-agent (child → father → child) hop.

    Attributes:
        round: 1-based debate round the forwarded turn belongs to.
        from_side: The side that produced ``content`` (the sender child).
        to_side: The opponent side the controller forwards it to (the receiver).
        type: The hop kind; defaults to :data:`~agent_debate.core.constants.
            LOOP_RELAY_MESSAGE_TYPE` so each envelope is self-describing.
        content: The raw (untrusted) debater text being forwarded. The legible
            adversarial frame the model sees is derived from this via
            :meth:`render` — the envelope stores the data, not the prompt.
    """

    model_config = ConfigDict(extra="forbid")

    round: int
    from_side: DebateSide
    to_side: DebateSide
    type: str = constants.LOOP_RELAY_MESSAGE_TYPE
    content: str

    def render(self, *, run_id: str | None = None) -> str:
        """Render the legible §5.6 adversarial relay text injected into the opponent.

        Reuses :func:`~agent_debate.core.agents.build_adversarial_relay` on
        :attr:`content` (sanitise + "«…». Rebut it." framing — never re-implemented),
        so the debater receives the SAME legible prompt as before the JSON envelope
        was introduced (debate quality and anti-sycophancy preserved).

        Args:
            run_id: Threaded to the sanitiser so a neutralised injection in
                :attr:`content` is logged (observability); ``None`` logs nothing.

        Returns:
            The adversarially framed, sanitised relay string for the opponent.
        """
        return build_adversarial_relay(self.content, run_id=run_id)

    def to_payload(self) -> dict[str, object]:
        """Return the JSON-mode ``dict`` of this envelope for structured logging."""
        return self.model_dump(mode="json")


__all__ = ["AgentMessage"]
