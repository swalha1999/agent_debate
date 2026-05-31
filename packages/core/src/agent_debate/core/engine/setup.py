"""Debate SETUP step — topic + private side assignment (issue #47, task 6.2).

Orchestration sub-PRD §3.1 (Flow step 1): "Setup — controller receives/sets the
topic, privately assigns Pro = FOR and Con = AGAINST, hides its own stance." This
module implements that **preparation** step only; it runs **no model call** (no
network — the actual model calls live in the loop, task 6.3, and route through the
API gatekeeper, Epic 13).

:func:`setup_debate` validates the (untrusted, user-supplied) topic with the 7.2
security validator (:func:`~agent_debate.core.security.validate_topic` — rejecting
abusive/oversized input with the clear typed error), then builds the three agents
(Pro, Con, Controller) and their three ISOLATED contexts
(:func:`~agent_debate.core.agents.create_debate_contexts`), and returns a typed
:class:`DebateSetup` carrying exactly what the loop (6.3) needs: the validated
topic, the three agents + contexts, the side assignment and the config.

**Private side assignment.** Pro is always FOR and Con always AGAINST — a fixed,
explicit mapping keyed by the :class:`DebateSide` constants (never hard-coded
strings) and owned as controller-managed state. **Controller neutrality:**
:class:`DebateSetup` carries NO controller stance/opinion field — the controller
is neutral (its system prompt already enforces "never reveal stance", task 5.3),
and the logged setup event likewise records no stance.

The setup logs one ``system`` event via the LOG package (run_id, the sanitised
topic, the assignment) so the step is observable; all literals come from
:mod:`agent_debate.core.constants` / :class:`DebateSide` (single source of truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_debate.core import constants
from agent_debate.core.agents import (
    DebateContexts,
    build_controller_system_prompt,
    build_debater_system_prompt,
    create_con_debater,
    create_controller,
    create_debate_contexts,
    create_pro_debater,
)
from agent_debate.core.agents.prompts import SIDE_LABEL
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.security import sanitize_untrusted_text, validate_topic
from agent_debate.core.settings import Settings, get_settings
from agent_debate.core.skills import DebateSide
from agent_debate.log import log_event
from pydantic_ai import Agent
from pydantic_ai.models import Model

#: Injectable per-agent models for offline tests: keys are the two
#: :class:`DebateSide` values plus the controller identity string.
SetupModels = dict[object, Model]

#: Identity key used in :data:`SetupModels` for the controller's injected model.
_CONTROLLER_KEY = constants.SETUP_LOG_AGENT

#: ``round`` recorded on the setup event — setup precedes the loop, so it is not
#: tied to a debate round (the engine binds the real round on later events).
_SETUP_ROUND = 0


@dataclass(frozen=True, slots=True)
class DebateSetup:
    """Prepared state for one debate run — the output of :func:`setup_debate`.

    Carries exactly what the loop (6.3) consumes: the validated ``topic``, the
    three agents (``pro_agent``/``con_agent``/``controller_agent``), their three
    isolated ``contexts``, the explicit side ``assignment`` and the ``config``.

    The assignment is fixed and structured: ``pro_side`` is always
    :attr:`DebateSide.PRO` (FOR) and ``con_side`` always :attr:`DebateSide.CON`
    (AGAINST). There is deliberately **no controller stance/opinion field** — the
    controller is neutral (anti-sycophancy §4 / task 5.3).
    """

    topic: str
    config: DebateConfig
    pro_agent: Agent[None, str]
    con_agent: Agent[None, str]
    controller_agent: Agent[None, str]
    contexts: DebateContexts
    pro_side: DebateSide = DebateSide.PRO
    con_side: DebateSide = DebateSide.CON

    @property
    def side_assignment(self) -> dict[DebateSide, str]:
        """The fixed FOR/AGAINST label per side (``PRO`` → FOR, ``CON`` → AGAINST)."""
        return {self.pro_side: SIDE_LABEL[self.pro_side], self.con_side: SIDE_LABEL[self.con_side]}


def setup_debate(
    topic: str,
    config: DebateConfig,
    *,
    settings: Settings | None = None,
    models: SetupModels | None = None,
    run_id: str | None = None,
    runs_dir: Path | str | None = None,
) -> DebateSetup:
    """Prepare a debate run: validate the topic, assign sides, build agents (§3.1).

    The ``topic`` is untrusted user input: it is validated by the 7.2 security
    validator (raising :class:`~agent_debate.core.security.InvalidInputError` on
    an empty/control-char/oversized topic). Pro is privately assigned FOR and Con
    AGAINST; the Controller stays neutral (no stance is set or exposed). The three
    agents are built on injected ``models`` (a ``TestModel`` per agent keeps tests
    offline) or, absent injection, from the configured model strings. **No model
    call is made here** — setup only prepares state.

    Args:
        topic: The user-supplied debate topic (validated before use).
        config: The validated run :class:`DebateConfig`.
        settings: Configuration to read; defaults to the process settings.
        models: Optional per-agent models keyed by :class:`DebateSide` /
            ``"controller"`` (tests inject ``TestModel`` to avoid network/key).
        run_id: When set, a ``system`` setup event is logged (else skipped).
        runs_dir: Optional run-log directory passed through to the LOG package.

    Returns:
        A :class:`DebateSetup` holding the prepared, loop-ready state.
    """
    validated_topic = validate_topic(topic)
    resolved_settings = settings or get_settings()
    injected = models or {}
    setup = DebateSetup(
        topic=validated_topic,
        config=config,
        pro_agent=create_pro_debater(
            resolved_settings, topic=validated_topic, model=injected.get(DebateSide.PRO)
        ),
        con_agent=create_con_debater(
            resolved_settings, topic=validated_topic, model=injected.get(DebateSide.CON)
        ),
        controller_agent=create_controller(resolved_settings, model=injected.get(_CONTROLLER_KEY)),
        contexts=create_debate_contexts(),
    )
    _attach_system_prompts(setup, resolved_settings, validated_topic)
    if run_id is not None:
        _log_setup(setup, run_id, runs_dir)
    return setup


def _attach_system_prompts(setup: DebateSetup, settings: Settings, topic: str) -> None:
    """Store each agent's system-prompt text on its OWN isolated context.

    pydantic-ai does not re-inject an agent's configured ``system_prompt`` once a
    run is given a ``message_history`` (which the engine always supplies), so the
    prompt is recorded on the per-agent :class:`~agent_debate.core.agents.context.
    AgentContext`; its ``message_history`` then embeds it as the leading
    ``SystemPromptPart`` (delivered to the model exactly once). The text is built
    from the SAME builders the agents use (single source of truth), so each side's
    own side/rules/skills/topic prompt stays isolated to its own thread (§5.4).
    """
    setup.contexts.pro.system_prompt = build_debater_system_prompt(
        DebateSide.PRO, topic=topic, max_words=settings.max_words
    )
    setup.contexts.con.system_prompt = build_debater_system_prompt(
        DebateSide.CON, topic=topic, max_words=settings.max_words
    )
    setup.contexts.controller.system_prompt = build_controller_system_prompt()


def _log_setup(setup: DebateSetup, run_id: str, runs_dir: Path | str | None) -> None:
    """Emit one ``system`` event recording the topic + assignment (no stance)."""
    payload: dict[str, object] = {
        "event": constants.SETUP_EVENT_TAG,
        "topic": sanitize_untrusted_text(setup.topic),
        "assignment": {
            setup.pro_side.value: SIDE_LABEL[setup.pro_side],
            setup.con_side.value: SIDE_LABEL[setup.con_side],
        },
    }
    kwargs = {"runs_dir": runs_dir} if runs_dir is not None else {}
    log_event(
        run_id=run_id,
        agent=constants.SETUP_LOG_AGENT,
        event_type=constants.SETUP_LOG_EVENT_TYPE,
        round=_SETUP_ROUND,
        payload=payload,
        **kwargs,  # type: ignore[arg-type]
    )


__all__ = ["DebateSetup", "SetupModels", "setup_debate"]
