"""The ``build_argument`` debate skill (TASKS.md 4.2, issue #33).

PRD §5.2: a debater calls ``build_argument`` to **structure** a persuasive
argument or rebuttal for its assigned side. This is the first agent skill
(Epic 4) and is intentionally *pure and deterministic* — it organises the
agent-supplied content (claim, supports, optional opponent point) into a typed
:class:`Argument`; it does **not** call an LLM or the network. The LLM provides
the content as tool arguments; the skill arranges it. Because no external API
call is made, the API gatekeeper (Epic 13) does not apply here.

Anti-sycophancy (``docs/prds/anti-sycophancy.md`` §2): when an ``opponent_point``
is supplied, the skill builds a ``rebuttal`` that *answers* it rather than
restating it — the debater must rebut, not concede.

Full registration as a real Pydantic AI tool is task 4.5; here we ship the
tool-ready function plus its validated input/output models (:class:`ArgumentRequest`
/ :class:`Argument`), re-exported from :mod:`agent_debate.core`.
"""

from __future__ import annotations

from agent_debate.core.constants import (
    CONCLUSION_TEMPLATE,
    REBUTTAL_LEAD_IN,
    REBUTTAL_LEAD_OUT,
)
from agent_debate.core.skills.models import Argument, ArgumentRequest
from agent_debate.log import get_logger

#: ``run_id`` used for the skill's standalone ``tool_call`` debug log line. A real
#: debate binds its own run via the LOG package; this pure skill does not require
#: one, so it logs under a stable module label (no hard-coded value inline).
_LOG_RUN_ID = "skills.build_argument"

_LOG = get_logger(_LOG_RUN_ID)


def _build_rebuttal(opponent_point: str | None) -> str | None:
    """Frame a rebuttal that links and answers the opponent's point.

    Returns ``None`` when no opponent point was supplied. Otherwise the opponent's
    point is quoted and explicitly contested (anti-sycophancy §2/§3), never merely
    restated.
    """
    if opponent_point is None:
        return None
    return f"{REBUTTAL_LEAD_IN}{opponent_point}{REBUTTAL_LEAD_OUT}"


def build_argument(request: ArgumentRequest) -> Argument:
    """Structure ``request`` into a persuasive :class:`Argument` for its side.

    Deterministic structuring only — the inputs are already validated by
    :class:`ArgumentRequest`, so this function never sees a bad payload. It maps
    the assigned side, claim and supports onto the output, derives a rebuttal that
    links the opponent's point when one is given, and composes a closing line that
    reasserts the claim for the side.

    Args:
        request: The validated, agent-supplied content to organise.

    Returns:
        The structured :class:`Argument`.
    """
    rebuttal = _build_rebuttal(request.opponent_point)
    conclusion = CONCLUSION_TEMPLATE.format(side=request.side.value, claim=request.claim)
    _LOG.debug(
        "tool_call",
        tool="build_argument",
        side=request.side.value,
        supports=len(request.supports),
        has_rebuttal=rebuttal is not None,
    )
    return Argument(
        side=request.side,
        claim=request.claim,
        supports=request.supports,
        rebuttal=rebuttal,
        conclusion=conclusion,
    )


__all__ = ["build_argument"]
