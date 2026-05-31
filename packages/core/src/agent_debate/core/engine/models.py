"""Typed debate configuration — :class:`DebateConfig` (issue #46, task 6.1).

Orchestration sub-PRD §2: a debate's **input** is a ``DebateConfig`` (rounds,
max_words, models, timeout, retries) plus a topic. This module defines that
config as a validated, JSON-serialisable Pydantic v2 model.

The defaults are **config-driven**, never hard-coded here: :meth:`DebateConfig.
from_settings` lifts every tunable from a :class:`~agent_debate.core.Settings`
instance (which itself reads the PRD §7 table / environment), so changing a
setting changes the derived config. The per-side ``pro_model`` / ``con_model``
honour the settings' resolved PRO/CON → DEBATER fallback (one source of truth).

This is the engine's **input contract** only — the 10-vs-10 loop that consumes it
lands in later Epic-6 tasks (6.2+). :class:`DebateResult` (the output) lives in
:mod:`agent_debate.core.engine.result`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from agent_debate.core.settings import Settings


class DebateConfig(BaseModel):
    """Validated, config-driven inputs for one debate run (sub-PRD §2).

    Frozen + ``extra="forbid"`` to match the project's model hardening; it
    round-trips through JSON so the CLI/API/UI can emit/replay a run's config.

    Attributes:
        rounds: Debate rounds per side (must be > 0).
        max_words: Word limit per debate message (must be > 0).
        turn_timeout_s: Per-turn timeout in seconds (must be > 0).
        max_retries: Retries on timeout/transient error (must be >= 0).
        debater_model: ``provider:model`` string for both debaters by default.
        controller_model: ``provider:model`` string for the controller/judge.
        pro_model: Resolved PRO-side model (override or ``debater_model``).
        con_model: Resolved CON-side model (override or ``debater_model``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rounds: int = Field(gt=0)
    max_words: int = Field(gt=0)
    turn_timeout_s: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    debater_model: str = Field(min_length=1)
    controller_model: str = Field(min_length=1)
    pro_model: str = Field(min_length=1)
    con_model: str = Field(min_length=1)

    @classmethod
    def from_settings(cls, settings: Settings) -> DebateConfig:
        """Build a config from a :class:`Settings` instance (no hard-coding).

        Every field is lifted from ``settings`` — including the resolved
        :pyattr:`Settings.pro_model` / :pyattr:`Settings.con_model` per-side
        fallback — so the config defaults track configuration exactly.
        """
        return cls(
            rounds=settings.rounds,
            max_words=settings.max_words,
            turn_timeout_s=settings.turn_timeout_s,
            max_retries=settings.max_retries,
            debater_model=settings.debater_model,
            controller_model=settings.controller_model,
            pro_model=settings.pro_model,
            con_model=settings.con_model,
        )


__all__ = ["DebateConfig"]
