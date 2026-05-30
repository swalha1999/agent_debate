"""Startup required-key validation (issue #23, task 2.3).

Task 2.1 keeps ``ANTHROPIC_API_KEY`` *optional* so importing :class:`Settings`
never explodes, and task 2.2's resolver constructs a provider client eagerly —
which, with the key absent, raises a deep Pydantic AI / SDK ``UserError`` whose
stack trace is opaque to an operator. This module fires *first* with a single,
clear, **actionable** error: it names the missing env var(s) and how to fix them
(set the var in ``.env`` — see ``.env.example``).

The required provider is derived from the *active* model strings (PRD §7:
``DEBATER_MODEL`` / ``CONTROLLER_MODEL`` / ``PRO_MODEL`` / ``CON_MODEL``). The
prefix before ``:`` selects the provider; the provider→env-var mapping lives in
:data:`agent_debate.core.constants.PROVIDER_KEY_ENV_VARS` (one source of truth,
extensible). Providers absent from the mapping are treated leniently — they are
not blocked, since their key requirements are not yet modelled.
"""

from __future__ import annotations

import os

from agent_debate.core import constants
from agent_debate.core.settings import Settings
from agent_debate.log import get_logger

_LOG = get_logger("validation")


class MissingApiKeyError(RuntimeError):
    """Raised when an active provider's required API key is absent/blank.

    Carries a human-readable, actionable message naming the missing env var(s)
    and how to fix them — deliberately surfaced *before* the deep SDK error.
    """


def _active_providers(settings: Settings) -> list[str]:
    """Return the distinct provider prefixes used by the active role models.

    Order-preserving so the error lists vars in a stable, predictable order.
    """
    model_strings = (
        settings.debater_model,
        settings.controller_model,
        settings.pro_model,
        settings.con_model,
    )
    providers: list[str] = []
    for model_string in model_strings:
        provider = model_string.split(":", 1)[0].strip().lower()
        if provider and provider not in providers:
            providers.append(provider)
    return providers


def validate_required_keys(settings: Settings) -> None:
    """Validate that every active provider's required API key is present.

    The active providers come from the role model strings; each mapped provider
    must have its key env var set to a non-blank value. Unmapped providers are
    skipped (lenient).

    :raises MissingApiKeyError: if one or more required keys are missing/blank —
        a single error naming each missing var and how to set it. This fires
        before the Pydantic AI / SDK ``UserError`` so operators see our message.
    """
    missing: list[str] = []
    for provider in _active_providers(settings):
        env_var = constants.PROVIDER_KEY_ENV_VARS.get(provider)
        if env_var is None:
            continue  # lenient: provider not modelled here
        value = os.environ.get(env_var)
        if (value is None or not value.strip()) and env_var not in missing:
            missing.append(env_var)

    if not missing:
        return

    names = ", ".join(missing)
    hint = (
        f"Set {names} in your environment or .env file "
        f"(copy .env.example to .env and fill in your key)."
    )
    message = f"Missing required API key(s): {names}. {hint}"
    _LOG.error("missing_api_key", missing=missing)
    raise MissingApiKeyError(message)


__all__ = ["MissingApiKeyError", "validate_required_keys"]
