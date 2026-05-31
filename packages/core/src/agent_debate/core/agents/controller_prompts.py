"""Controller (moderator/judge) system-prompt builder + its text constants (TASKS.md 5.3).

PRD §5.3 / ``docs/prds/anti-sycophancy.md`` §4 require the **controller** to moderate and
judge the debate while it **knows both assigned sides** (Pro = FOR, Con = AGAINST) yet
**never reveals its own stance or opinion** ("Controller never reveals its own stance").
It must **detect drift** (a debater starting to agree with / restate the opponent) and
**nudge privately** — a correction that is logged and surfaced but does **not** count as a
debate turn — and at the end render a structured **verdict**.

This module is the single source of truth for that prompt text. It is split out of
``prompts.py`` (the debater builder) so each file stays well under the 150-line limit.
No values are inlined: the skill list (:data:`CONTROLLER_SKILLS`, with one-line "when to
use" each) and every rule/instruction line are named constants.
"""

from __future__ import annotations

#: The named controller skills the prompt lists, in PRD §5.3 order. Single source of
#: truth so the prompt and the eventual tool registration cannot drift apart. These
#: mirror the skills in :mod:`agent_debate.core.skills.controller`.
CONTROLLER_SKILLS: tuple[str, ...] = ("assess_drift", "nudge", "render_verdict")

#: One-line "when to use" guidance per controller skill (PRD §5.3), keyed by name.
CONTROLLER_SKILL_USAGE: dict[str, str] = {
    "assess_drift": (
        "call after each debater message to check whether that debater is drifting — "
        "agreeing with, conceding to, or merely restating the opponent."
    ),
    "nudge": (
        "call when drift is detected to send a private correction pulling the debater "
        "back to its assigned side; this does NOT count as a debate turn."
    ),
    "render_verdict": ("call once at the end to produce the structured, debate-derived verdict."),
}

#: Opening line — states the controller role (it moderates AND judges).
ROLE_LINE = (
    "You are the Controller: you moderate and judge a two-sided debate. You are the "
    "neutral arbiter, not a participant."
)

#: States that the controller knows both assigned sides. ``{pro}`` / ``{con}`` are labels.
SIDES_LINE = (
    "You know both assigned sides: the Pro debater argues the {pro} side and the Con "
    "debater argues the {con} side."
)

#: The neutrality rules block (anti-sycophancy §4: controller never reveals its stance).
NEUTRALITY_TEMPLATE = (
    "Neutrality rules:\n"
    "- NEVER reveal your own stance or opinion, and never hint which side you lean "
    "toward. You hold no stance.\n"
    "- Judge only from the debate itself; your verdict declares a debate-derived "
    "outcome, never a personal preference."
)

#: The moderation rules block (drift detection + private nudge + final verdict).
MODERATION_TEMPLATE = (
    "Moderation duties:\n"
    "- Detect drift: after each message, check whether that debater is starting to "
    "agree with, concede to, or merely restate the opponent instead of rebutting.\n"
    "- Nudge privately when a debater drifts: send a private correction that pulls it "
    "back to its assigned side. A nudge is private and does NOT count as a debate "
    "turn.\n"
    "- Render a verdict at the end: produce a single structured verdict for the debate."
)

#: Heading introducing the explicit controller-skill list.
SKILLS_HEADER = "You have these skills (tools) — use each when noted:"

#: Per-skill bullet template; ``{name}`` is the skill, ``{usage}`` its when-to-use.
SKILL_LINE_TEMPLATE = "- {name}: {usage}"

#: Default side labels (Pro = FOR, Con = AGAINST) — mirror the debater ``SIDE_LABEL``.
PRO_LABEL = "FOR"
CON_LABEL = "AGAINST"


def build_controller_system_prompt(
    *,
    pro_label: str = PRO_LABEL,
    con_label: str = CON_LABEL,
    skills: tuple[str, ...] = CONTROLLER_SKILLS,
) -> str:
    """Build the Controller's moderator/judge system prompt (PRD §5.3, anti-sycophancy §4).

    The returned text states the controller moderates and judges, knows both assigned
    sides (``pro_label`` / ``con_label``, default FOR / AGAINST), must NEVER reveal its
    own stance or opinion, must detect drift and nudge privately (a nudge does not count
    as a debate turn), and must render a verdict at the end — then lists the named
    ``skills`` with a one-line "when to use" each.

    Args:
        pro_label: Label for the Pro debater's side (default ``"FOR"``).
        con_label: Label for the Con debater's side (default ``"AGAINST"``).
        skills: The named controller skills to list; defaults to :data:`CONTROLLER_SKILLS`.

    Returns:
        The assembled system-prompt string.
    """
    sides_line = SIDES_LINE.format(pro=pro_label, con=con_label)
    skill_lines = [
        SKILL_LINE_TEMPLATE.format(name=name, usage=CONTROLLER_SKILL_USAGE[name]) for name in skills
    ]
    skills_block = "\n".join([SKILLS_HEADER, *skill_lines])
    return "\n\n".join(
        [ROLE_LINE, sides_line, NEUTRALITY_TEMPLATE, MODERATION_TEMPLATE, skills_block]
    )


__all__ = ["CONTROLLER_SKILLS", "build_controller_system_prompt"]
