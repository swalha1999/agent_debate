"""The ``analyze_opponent_argument`` debate skill (TASKS.md 4.3, issue #34).

PRD §5.2: a debater calls ``analyze_opponent_argument`` to **dissect** the
opponent's last message — surface its weaknesses/assumptions and **decide what to
rebut**. Like :func:`build_argument` this is the second agent skill (Epic 4) and is
intentionally *pure and deterministic*: it organises the agent-supplied content
(the opponent message, the analysing side, any flagged weaknesses) into a typed
:class:`OpponentAnalysis`; it does **not** call an LLM or the network. The LLM
provides the judgement as tool arguments; the skill arranges it. Because no
external API call is made, the API gatekeeper (Epic 13) does not apply here.

Anti-sycophancy (``docs/prds/anti-sycophancy.md`` §2): the skill always yields a
concrete ``rebuttal_target`` — the agent's strongest flagged weakness, or the
opponent's lead claim when none were flagged — so the agent targets and rebuts
rather than conceding.

The output composes with :func:`build_argument`: ``rebuttal_target`` is a ready
value for :class:`ArgumentRequest`'s ``opponent_point``. Full Pydantic AI tool
registration is task 4.5; here we ship the tool-ready function plus its models.
"""

from __future__ import annotations

from agent_debate.core.constants import CLAIM_SPLIT_DELIMITERS
from agent_debate.core.skills.models import OpponentAnalysis, OpponentAnalysisRequest
from agent_debate.log import get_logger

#: ``run_id`` for the skill's standalone ``tool_call`` debug line. A real debate
#: binds its own run via the LOG package; this pure skill logs under a stable
#: module label (no hard-coded value inline).
_LOG_RUN_ID = "skills.analyze_opponent_argument"

_LOG = get_logger(_LOG_RUN_ID)


def _extract_claims(opponent_message: str) -> list[str]:
    """Split ``opponent_message`` into its key claims, one per sentence.

    Sentences are delimited by :data:`CLAIM_SPLIT_DELIMITERS`; blank fragments are
    dropped. The whole (trimmed) message is always at least one claim, so the list
    is never empty for a validated, non-empty input.
    """
    claims: list[str] = []
    buffer = ""
    for char in opponent_message:
        if char in CLAIM_SPLIT_DELIMITERS:
            sentence = buffer.strip()
            if sentence:
                claims.append(sentence)
            buffer = ""
        else:
            buffer += char
    tail = buffer.strip()
    if tail:
        claims.append(tail)
    return claims


def analyze_opponent_argument(request: OpponentAnalysisRequest) -> OpponentAnalysis:
    """Dissect ``request`` into a structured :class:`OpponentAnalysis`.

    Deterministic structuring only — the input is already validated by
    :class:`OpponentAnalysisRequest`. It extracts the opponent's key claims, carries
    the flagged weaknesses through, and prioritises a single ``rebuttal_target``:
    the first (strongest) flagged weakness, or — when none were flagged — the
    opponent's lead claim, so the agent always has a concrete point to rebut.

    Args:
        request: The validated, agent-supplied content to organise.

    Returns:
        The structured :class:`OpponentAnalysis`.
    """
    claims = _extract_claims(request.opponent_message)
    rebuttal_target = request.weaknesses[0] if request.weaknesses else claims[0]
    _LOG.debug(
        "tool_call",
        tool="analyze_opponent_argument",
        side=request.side.value,
        claims=len(claims),
        weaknesses=len(request.weaknesses),
    )
    return OpponentAnalysis(
        side=request.side,
        claims=claims,
        weaknesses=request.weaknesses,
        rebuttal_target=rebuttal_target,
    )


__all__ = ["analyze_opponent_argument"]
