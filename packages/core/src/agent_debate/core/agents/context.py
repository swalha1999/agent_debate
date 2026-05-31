"""Independent per-agent conversation contexts (TASKS.md 5.4, issue #41).

PRD §5.4 / anti-sycophancy ``docs/prds/anti-sycophancy.md`` §2: the two debaters
must **never share a chat thread** (sycophancy mitigation). Each agent — Pro, Con
and the Controller — keeps its OWN ordered message history; mutating one context
never touches another. This module is the **plumbing only**: it builds the
isolated containers the run loop (Epic 6) feeds to ``agent.run(message_history=…)``.

**Context representation.** A context holds a lightweight, typed :class:`Turn`
record (``role`` + ``content``) per message rather than raw pydantic-ai
``ModelMessage`` objects. The typed record keeps the container trivially
isolatable, JSON-friendly and easy for tasks 5.5/5.6 to extend; it maps to
pydantic-ai ``message_history`` at run time via :func:`Turn.to_model_message`
(``user`` → ``ModelRequest[UserPromptPart]``, ``assistant`` → ``ModelResponse``).

This module builds **no agent and makes no network call** — there is no external
call here, so the API gatekeeper (Epic 13) does not apply.

Seams for later tasks: 5.5 (side-anchoring re-injection) and 5.6 (adversarial
relay framing) append the opponent's *already-framed* message as a ``user`` turn
in the agent's OWN thread via :meth:`AgentContext.append_user` — never by sharing
the opponent's raw history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from agent_debate.core.skills import DebateSide
from agent_debate.log import get_logger
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

_LOG = get_logger("agents")

#: Stable identity string for the Controller's own context. Debater contexts use
#: their :class:`DebateSide` value (``"pro"``/``"con"``); kept here so the role
#: label is defined once and never hard-coded at call sites.
CONTROLLER_IDENTITY = "controller"

#: The two conversational roles a turn can take. ``user`` is an inbound prompt
#: (topic, side anchor, or a framed opponent message); ``assistant`` is the
#: agent's own reply. Named here so callers never pass a free-form role string.
Role = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class Turn:
    """One immutable message in an agent's own history (``role`` + ``content``).

    Frozen so a history snapshot cannot be mutated in place. :meth:`to_model_message`
    maps it onto the pydantic-ai ``message_history`` shape the engine (Epic 6)
    feeds to ``agent.run(message_history=…)``.
    """

    role: Role
    content: str

    def to_model_message(self) -> ModelMessage:
        """Render this turn as the pydantic-ai ``ModelMessage`` for a run history."""
        if self.role == "user":
            return ModelRequest(parts=[UserPromptPart(content=self.content)])
        return ModelResponse(parts=[TextPart(content=self.content)])


@dataclass(slots=True)
class AgentContext:
    """One agent's **own** conversation history — isolated from every other agent.

    Holds an ``identity`` (``"pro"``/``"con"``/``"controller"``), the agent's own
    ``system_prompt`` text and a private, ordered list of :class:`Turn` records.
    Appending to one context never affects another (no shared thread — the core
    anti-sycophancy property). Pass :meth:`message_history` to ``agent.run`` to
    thread this agent's OWN history back into ITS next run.

    **System-prompt delivery (issue: system-prompt-delivery).** pydantic-ai only
    injects an :class:`~pydantic_ai.Agent`'s configured ``system_prompt`` when a
    run STARTS with no ``message_history``; once a history is supplied it is NOT
    re-injected. Because the engine always runs debaters with ``message_history``,
    the configured prompt would never reach the model. So the agent's own prompt
    text is stored HERE and :meth:`message_history` embeds it as the leading
    :class:`~pydantic_ai.messages.SystemPromptPart` of the FIRST request — exactly
    once — keeping each agent's prompt isolated to its own thread (§5.4).
    """

    identity: str
    system_prompt: str | None = None
    _turns: list[Turn] = field(default_factory=list)

    def append_user(self, content: str) -> None:
        """Append an inbound ``user`` turn (prompt / side anchor / framed opponent)."""
        self._turns.append(Turn(role="user", content=content))

    def append_assistant(self, content: str) -> None:
        """Append the agent's own ``assistant`` reply turn."""
        self._turns.append(Turn(role="assistant", content=content))

    def history(self) -> tuple[Turn, ...]:
        """Return an immutable snapshot of this agent's ordered turns (a copy)."""
        return tuple(self._turns)

    def message_history(self) -> list[ModelMessage]:
        """Render this agent's history as pydantic-ai ``message_history`` for a run.

        When a :attr:`system_prompt` is set it is prepended as a
        :class:`~pydantic_ai.messages.SystemPromptPart` on the FIRST
        :class:`~pydantic_ai.messages.ModelRequest` (the leading ``user`` turn), so
        pydantic-ai delivers the agent's full system prompt to the model exactly
        once — not repeated on every turn (see the class docstring).
        """
        history = [turn.to_model_message() for turn in self._turns]
        if self.system_prompt is not None:
            self._prepend_system_prompt(history)
        return history

    def _prepend_system_prompt(self, history: list[ModelMessage]) -> None:
        """Insert the system prompt at the head of the first ``ModelRequest``.

        The leading request is the very first inbound turn of the run history; it
        is rebuilt with the prompt part in front (``ModelRequest.parts`` is a typed
        sequence, so we replace the request rather than mutate it in place). A
        history with no ``ModelRequest`` yet (e.g. a not-yet-prompted thread) gets a
        standalone request carrying only the prompt.
        """
        prompt_part = SystemPromptPart(content=self.system_prompt or "")
        for index, message in enumerate(history):
            if isinstance(message, ModelRequest):
                history[index] = ModelRequest(parts=[prompt_part, *message.parts])
                return
        history.insert(0, ModelRequest(parts=[prompt_part]))


@dataclass(frozen=True, slots=True)
class DebateContexts:
    """Holder owning the three **distinct** per-agent contexts, exposed by role.

    ``pro``, ``con`` and ``controller`` are separate :class:`AgentContext` objects
    with independent histories — the holder never merges them into one thread.
    """

    pro: AgentContext
    con: AgentContext
    controller: AgentContext

    def for_side(self, side: DebateSide) -> AgentContext:
        """Return the debater context for ``side`` (``PRO`` → ``pro``, ``CON`` → ``con``)."""
        return self.pro if side is DebateSide.PRO else self.con


def create_debate_contexts() -> DebateContexts:
    """Build three isolated contexts (Pro, Con, Controller) for one debate run.

    Each agent gets its OWN empty :class:`AgentContext`; the returned objects are
    distinct, so a turn appended to one never appears in another (anti-sycophancy
    §2 — debaters never share a chat thread).
    """
    _LOG.debug("debate_contexts_created", agents=3)
    return DebateContexts(
        pro=AgentContext(identity=DebateSide.PRO.value),
        con=AgentContext(identity=DebateSide.CON.value),
        controller=AgentContext(identity=CONTROLLER_IDENTITY),
    )


__all__ = [
    "CONTROLLER_IDENTITY",
    "AgentContext",
    "DebateContexts",
    "Role",
    "Turn",
    "create_debate_contexts",
]
