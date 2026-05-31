"""Per-turn side anchoring — re-inject the agent's side every turn (issue #42).

Anti-sycophancy (``docs/prds/anti-sycophancy.md`` §2 mechanism 2): "Side anchoring
every turn. Re-inject the agent's side (FOR/AGAINST) + an explicit 'do not concede
merely because the opponent is convincing' instruction." This is in **addition** to
the debater system prompt (``prompts.py``) — a per-TURN reminder injected into the
agent's OWN context right before it generates each turn.

:func:`build_side_anchor` is the pure text builder; :func:`anchor_turn` is the
injection helper that appends the anchor as a ``user`` turn into THAT agent's own
:class:`~agent_debate.core.agents.context.AgentContext` (reusing the 5.4 isolation —
it never touches the opponent's history). It composes with the 5.6 adversarial
relay: an already-framed ``opponent_message`` is folded into the SAME user turn.

DRY: the anti-concession wording is the shared :data:`~agent_debate.core.agents.
prompts.ANTI_CONCESSION_RULE` constant — written once for both prompt and anchor.
All other labels/templates are named constants; ``max_words`` (when shown) comes
from config, never hard-coded. No external/network call — the gatekeeper (Epic 13)
does not apply.
"""

from __future__ import annotations

from agent_debate.core.agents.context import AgentContext
from agent_debate.core.agents.prompts import ANTI_CONCESSION_RULE, SIDE_LABEL
from agent_debate.core.skills import DebateSide
from agent_debate.log import get_logger

_LOG = get_logger("agents")

#: Lead line of the per-turn reminder; ``{label}`` is the FOR/AGAINST side label.
ANCHOR_SIDE_LINE = "Reminder: you are arguing {label} the topic."

#: Closing nudge — restates the turn-level duty to stay on side and rebut.
ANCHOR_REBUT_LINE = "Stay on your side and rebut the opponent."

#: Optional word-limit reminder; ``{max_words}`` is supplied from config (Settings).
ANCHOR_WORD_LIMIT_LINE = "Keep your answer within {max_words} words."


def build_side_anchor(side: DebateSide, *, max_words: int | None = None) -> str:
    """Build the concise per-turn side-anchor reminder for ``side`` (§2 mechanism 2).

    States the assigned side (FOR/AGAINST), the shared anti-concession instruction
    (:data:`ANTI_CONCESSION_RULE` — "do not concede merely because the opponent is
    convincing"), and a stay-on-side-and-rebut nudge. When ``max_words`` is given a
    word-limit reminder is appended (read from config by the caller, never inlined).

    Args:
        side: The assigned stance — ``PRO`` (FOR) or ``CON`` (AGAINST).
        max_words: Optional per-message word limit to remind the debater of.

    Returns:
        The assembled single-paragraph anchor string.
    """
    lines = [
        ANCHOR_SIDE_LINE.format(label=SIDE_LABEL[side]),
        ANTI_CONCESSION_RULE,
        ANCHOR_REBUT_LINE,
    ]
    if max_words is not None:
        lines.append(ANCHOR_WORD_LIMIT_LINE.format(max_words=max_words))
    return " ".join(lines)


def anchor_turn(
    context: AgentContext,
    side: DebateSide,
    *,
    max_words: int | None = None,
    opponent_message: str | None = None,
) -> str:
    """Inject the per-turn side anchor into ``context`` (the agent's OWN history).

    Appends a single ``user`` turn carrying the side anchor — and, when given, the
    already-framed 5.6 ``opponent_message`` folded into the SAME turn (anchor first,
    so the side reminder leads every round). Only ``context`` is mutated, so the
    opponent's history is untouched (5.4 isolation). Returns the injected text so
    the run loop can log/surface exactly what the debater saw.

    Args:
        context: The debater's own :class:`AgentContext` to append into.
        side: The agent's assigned stance — used to pick the FOR/AGAINST anchor.
        max_words: Optional word limit to include in the anchor (from config).
        opponent_message: Optional already-framed opponent relay (task 5.6) to
            append below the anchor in the same user turn.

    Returns:
        The exact text appended to ``context``.
    """
    anchor = build_side_anchor(side, max_words=max_words)
    content = f"{anchor}\n\n{opponent_message}" if opponent_message else anchor
    context.append_user(content)
    _LOG.debug("side_anchor_injected", identity=context.identity, side=side.value)
    return content


__all__ = ["ANTI_CONCESSION_RULE", "anchor_turn", "build_side_anchor"]
