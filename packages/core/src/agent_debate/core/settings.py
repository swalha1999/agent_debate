"""Runtime configuration for agent_debate (PRD §7, issue #21 / task 2.1).

A :class:`pydantic_settings.BaseSettings` model that loads every PRD §7 field
from the process environment and an optional ``.env`` file, with defaults that
match the PRD §7 table exactly (single source of truth in
:mod:`agent_debate.core.constants`).

Design notes (issue #21):

* PRD §7 vars are *bare* names (``ROUNDS``, ``DEBATER_MODEL`` …), so the model
  uses **no env prefix** and is case-insensitive.
* ``ANTHROPIC_API_KEY`` is required for real provider calls, but is typed
  ``Optional`` here so importing/instantiating ``Settings`` never explodes —
  e.g. during test collection or in key-free packages. Strict "fail fast with a
  clear error when the key is missing" validation is a separate task (2.3).
* ``PRO_MODEL`` / ``CON_MODEL`` are optional per-side overrides; the resolved
  :pyattr:`pro_model` / :pyattr:`con_model` properties fall back to
  ``DEBATER_MODEL`` when unset.
"""

from __future__ import annotations

import os
from functools import lru_cache

from agent_debate.core import constants
from agent_debate.log import get_logger
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOG = get_logger("settings")


class Settings(BaseSettings):
    """Typed view of the PRD §7 configuration, loaded from env / ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    #: Default provider key — required for real runs; ``None`` keeps import safe
    #: (strict required-key validation is task 2.3).
    anthropic_api_key: str | None = Field(default=None)

    #: Model used for both debaters unless a per-side override is set.
    debater_model: str = Field(default=constants.DEFAULT_DEBATER_MODEL)

    #: Model used for the controller / judge agent.
    controller_model: str = Field(default=constants.DEFAULT_CONTROLLER_MODEL)

    #: Optional PRO-side model override (env ``PRO_MODEL``); see :pyattr:`pro_model`.
    pro_model_override: str | None = Field(default=None, alias="PRO_MODEL")

    #: Optional CON-side model override (env ``CON_MODEL``); see :pyattr:`con_model`.
    con_model_override: str | None = Field(default=None, alias="CON_MODEL")

    #: Rounds per agent.
    rounds: int = Field(default=constants.DEFAULT_ROUNDS)

    #: Word limit per debate message.
    max_words: int = Field(default=constants.DEFAULT_MAX_WORDS)

    #: Per-turn timeout in seconds.
    turn_timeout_s: int = Field(default=constants.DEFAULT_TURN_TIMEOUT_S)

    #: Retries on timeout / error.
    max_retries: int = Field(default=constants.DEFAULT_MAX_RETRIES)

    #: Selects the ``SearchProvider`` plug-in (e.g. ``duckduckgo``/``tavily``).
    search_backend: str = Field(default=constants.DEFAULT_SEARCH_BACKEND)

    #: Key for search backends that need one (ignored by DuckDuckGo).
    search_api_key: str | None = Field(default=None)

    #: Configurable USD budget cap per run; ``0.0`` (default) = unlimited (15.3).
    budget_usd: float = Field(default=constants.DEFAULT_BUDGET_USD, ge=0.0)

    #: Watchdog keep-alive heartbeat interval in seconds (issue #216, HW2 §8.6).
    watchdog_heartbeat_interval_s: float = Field(
        default=constants.DEFAULT_WATCHDOG_HEARTBEAT_INTERVAL_S, gt=0.0
    )

    #: Watchdog liveness timeout in seconds: a heartbeat stale past this = fallen.
    watchdog_liveness_timeout_s: float = Field(
        default=constants.DEFAULT_WATCHDOG_LIVENESS_TIMEOUT_S, gt=0.0
    )

    #: Maximum times the Watchdog restarts a fallen worker before giving up.
    watchdog_max_restarts: int = Field(default=constants.DEFAULT_WATCHDOG_MAX_RESTARTS, ge=0)

    @property
    def pro_model(self) -> str:
        """Resolved PRO-side model — ``PRO_MODEL`` or ``DEBATER_MODEL``."""
        return self.pro_model_override or self.debater_model

    @property
    def con_model(self) -> str:
        """Resolved CON-side model — ``CON_MODEL`` or ``DEBATER_MODEL``."""
        return self.con_model_override or self.debater_model


#: Mapping of ``Settings`` field → canonical ``os.environ`` key name.
#: Only fields whose value should be propagated to the OS environment are listed.
_ENV_PROPAGATION_MAP: tuple[tuple[str, str], ...] = (
    ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    ("search_api_key", "SEARCH_API_KEY"),
)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached :class:`Settings` instance.

    Cached so the ``.env`` / environment is read once. Tests that mutate the
    environment call :pymeth:`get_settings.cache_clear` to force a reload.

    Side-effect: after constructing :class:`Settings`, any field listed in
    :data:`_ENV_PROPAGATION_MAP` whose value is non-``None`` is written to
    ``os.environ`` via :func:`os.environ.setdefault` — i.e. **only if the key
    is not already present in the OS environment**.  This ensures that
    downstream libraries (e.g. pydantic-ai's Anthropic provider) which read
    ``os.environ`` directly can find values that were loaded only from a
    ``.env`` file, without silently overriding an explicit shell-level override.
    """
    settings = Settings()
    _LOG.debug(
        "settings_loaded",
        rounds=settings.rounds,
        max_words=settings.max_words,
        search_backend=settings.search_backend,
    )
    for attr, env_key in _ENV_PROPAGATION_MAP:
        value: str | None = getattr(settings, attr, None)
        if value is not None:
            os.environ.setdefault(env_key, value)
    return settings


__all__ = ["Settings", "get_settings"]
