"""Debater system-prompt builder + its text constants (TASKS.md 5.1, issue #38).

PRD §5.2 requires each debater's **system prompt** to state its side, the rules
(word limit, must rebut), and an **explicit list of the skills it has and when to
use them**. This module is the single source of truth for that text, so both the
Pro debater (task 5.1) and the Con debater (task 5.2) build their prompts here —
only the :class:`~agent_debate.core.skills.DebateSide` differs.

Anti-sycophancy (``docs/prds/anti-sycophancy.md`` §2) is baked into the rules: the
debater MUST rebut the opponent and must **not concede merely because the opponent
sounds convincing** (side-anchoring). The word limit is **config-driven** — it is
passed in from :class:`~agent_debate.core.Settings`, never hard-coded here.

No values are inlined: the side labels, rule templates and the skill list
(:data:`DEBATER_SKILLS`, with one-line "when to use" each) are named constants.
"""

from __future__ import annotations

from agent_debate.core.skills import DebateSide

#: The named skills every debater is told it can call, in the PRD §5.2 order.
#: A single source of truth so the Con debater (task 5.2) reuses the same list and
#: the prompt and the eventual tool registration (task 4.5) cannot drift apart.
#: ``web_search`` is named here only — the skill itself is task 4.1 (not yet built).
DEBATER_SKILLS: tuple[str, ...] = (
    "web_search",
    "build_argument",
    "analyze_opponent_argument",
)

#: One-line "when to use" guidance per skill (PRD §5.2), keyed by skill name. Kept
#: beside :data:`DEBATER_SKILLS` so every named skill has a usage note.
SKILL_USAGE: dict[str, str] = {
    "web_search": (
        "call when you need an external fact or source to back a point "
        "(provider-agnostic; never name a specific search vendor)."
    ),
    "build_argument": ("call to structure a persuasive argument or rebuttal for your side."),
    "analyze_opponent_argument": (
        "call to dissect the opponent's last message, find its weaknesses, "
        "and decide what to answer."
    ),
}

#: Human-readable label per side, stated explicitly in the prompt (PRD §5.2).
SIDE_LABEL: dict[DebateSide, str] = {
    DebateSide.PRO: "FOR",
    DebateSide.CON: "AGAINST",
}

#: Opening line — states the assigned side. ``{label}`` is FOR/AGAINST.
SIDE_LINE = "You are a debate agent arguing the {label} side of the topic."

#: The rules block (anti-sycophancy §2). ``{max_words}`` is injected from config.
RULES_TEMPLATE = (
    "Rules:\n"
    "- Answer in at most {max_words} words.\n"
    "- You MUST rebut the opponent's argument directly; never ignore it.\n"
    "- Do NOT concede merely because the opponent sounds convincing — "
    "hold your assigned side and keep arguing it."
)

#: Heading introducing the explicit skill list.
SKILLS_HEADER = "You have these skills (tools) — use each when noted:"

#: Per-skill bullet template; ``{name}`` is the skill, ``{usage}`` its when-to-use.
SKILL_LINE_TEMPLATE = "- {name}: {usage}"


def build_debater_system_prompt(
    side: DebateSide,
    *,
    max_words: int,
    skills: tuple[str, ...] = DEBATER_SKILLS,
) -> str:
    """Build a debater's system prompt for ``side`` (PRD §5.2, anti-sycophancy §2).

    The returned text states the assigned side (FOR/AGAINST), the rules (answer in
    ``<= max_words`` words; you MUST rebut; do not concede merely because the
    opponent is convincing), and an explicit list of the named ``skills`` with a
    one-line "when to use" each.

    Args:
        side: The assigned stance — ``PRO`` (FOR) or ``CON`` (AGAINST).
        max_words: The per-message word limit, supplied from
            :class:`~agent_debate.core.Settings` (never hard-coded).
        skills: The named skills to list; defaults to :data:`DEBATER_SKILLS`.

    Returns:
        The assembled system-prompt string.
    """
    side_line = SIDE_LINE.format(label=SIDE_LABEL[side])
    rules = RULES_TEMPLATE.format(max_words=max_words)
    skill_lines = [
        SKILL_LINE_TEMPLATE.format(name=name, usage=SKILL_USAGE[name]) for name in skills
    ]
    skills_block = "\n".join([SKILLS_HEADER, *skill_lines])
    return "\n\n".join([side_line, rules, skills_block])


__all__ = ["DEBATER_SKILLS", "build_debater_system_prompt"]
