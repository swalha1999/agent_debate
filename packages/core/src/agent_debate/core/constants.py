"""Default configuration values — the single source of truth (PRD §7, §7.2).

The guideline forbids hard-coded values scattered through the code (§7.2): the
PRD §7 defaults live here once and are referenced by :mod:`agent_debate.core.
settings`. Every name maps one-to-one to a row of the PRD §7 configuration
table so the two stay verifiably in sync.
"""

from __future__ import annotations

#: Default model for both debaters when no per-side override is given (PRD §7).
DEFAULT_DEBATER_MODEL = "anthropic:claude-sonnet-4-6"

#: Default model for the controller / judge agent (PRD §7).
DEFAULT_CONTROLLER_MODEL = "anthropic:claude-opus-4-8"

#: Rounds per agent (PRD §7).
DEFAULT_ROUNDS = 10

#: Word limit per debate message (PRD §7).
DEFAULT_MAX_WORDS = 150

#: Per-turn timeout in seconds (PRD §7).
DEFAULT_TURN_TIMEOUT_S = 60

#: Retries on timeout/error (PRD §7).
DEFAULT_MAX_RETRIES = 2

#: Selects the ``SearchProvider`` plug-in; DuckDuckGo needs no key (PRD §7).
DEFAULT_SEARCH_BACKEND = "duckduckgo"

#: Maps a ``provider:model`` prefix (the part before ``:``) to the environment
#: variable that must hold that provider's API key. The single source of truth
#: for startup key validation (task 2.3) — extend this dict to cover a new
#: provider. Providers absent from this map are treated leniently (not blocked),
#: because their key requirements are not yet modelled here.
PROVIDER_KEY_ENV_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}

__all__ = [
    "DEFAULT_CONTROLLER_MODEL",
    "DEFAULT_DEBATER_MODEL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_WORDS",
    "DEFAULT_ROUNDS",
    "DEFAULT_SEARCH_BACKEND",
    "DEFAULT_TURN_TIMEOUT_S",
    "PROVIDER_KEY_ENV_VARS",
]
