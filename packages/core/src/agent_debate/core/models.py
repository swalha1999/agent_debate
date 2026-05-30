"""Model resolver — ``provider:model`` strings → Pydantic AI models (task 2.2).

PRD §4 picks **Pydantic AI** as the LLM abstraction precisely so a provider is
swapped by *changing a config string*, with no ecosystem lock-in. This module
is the one place that turns the PRD §7 model strings (``DEBATER_MODEL`` /
``CONTROLLER_MODEL`` / ``PRO_MODEL`` / ``CON_MODEL``) into concrete model
objects, so the "swap with zero code changes" promise is config-driven:

* :func:`resolve_model` wraps :func:`pydantic_ai.models.infer_model` — the model
  is chosen entirely by the ``provider:model`` string (Anthropic is the PRD §7
  default, encoded in the string, not hard-coded here). A malformed/unknown
  string raises a clear error rather than silently yielding a broken model
  (strict required-key validation is task 2.3).
* :func:`resolve_models` maps a :class:`~agent_debate.core.Settings` instance to
  a typed :class:`ResolvedModels` struct for the four roles, reusing the
  settings' computed :pyattr:`pro_model` / :pyattr:`con_model` properties so the
  PRO/CON → DEBATER fallback lives in exactly one place.

This module only *constructs* model objects; it never calls a provider. Actual
execution must route every external call through the API gatekeeper (Epic 13),
which will drive these resolved models — wiring added by that later task.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_debate.core.settings import Settings
from agent_debate.core.validation import validate_required_keys
from agent_debate.log import get_logger
from pydantic_ai.models import Model, infer_model

_LOG = get_logger("models")


def resolve_model(model_string: str) -> Model:
    """Resolve a ``provider:model`` string to a Pydantic AI :class:`Model`.

    The provider is selected purely by the string (e.g. ``anthropic:…`` →
    Anthropic, ``openai:…`` → OpenAI), so swapping providers is a config-only
    change. Construction is offline — no network/API call is made here.

    :raises ValueError: if the provider/model string is unknown or malformed —
        Pydantic AI's :func:`infer_model` fails loudly rather than returning a
        broken model.
    """
    return infer_model(model_string)


@dataclass(frozen=True, slots=True)
class ResolvedModels:
    """The four debate roles resolved to concrete Pydantic AI models.

    ``pro`` / ``con`` already honour the PRO/CON → DEBATER fallback (resolved
    from :pyattr:`Settings.pro_model` / :pyattr:`Settings.con_model`).
    """

    debater: Model
    controller: Model
    pro: Model
    con: Model


def resolve_models(settings: Settings) -> ResolvedModels:
    """Resolve every PRD §7 role model from a :class:`Settings` instance.

    Resolution is driven entirely by the settings strings: ``PRO_MODEL`` /
    ``CON_MODEL`` fall back to ``DEBATER_MODEL`` via the settings' computed
    :pyattr:`Settings.pro_model` / :pyattr:`Settings.con_model` properties, so
    the fallback rule is defined in one place only.

    Required-key validation (task 2.3) runs *first*, so a missing provider key
    surfaces a clear :class:`~agent_debate.core.validation.MissingApiKeyError`
    naming the env var — never the deep Pydantic AI / SDK ``UserError`` that the
    eager client construction below would otherwise raise.
    """
    validate_required_keys(settings)
    resolved = ResolvedModels(
        debater=resolve_model(settings.debater_model),
        controller=resolve_model(settings.controller_model),
        pro=resolve_model(settings.pro_model),
        con=resolve_model(settings.con_model),
    )
    _LOG.debug(
        "models_resolved",
        debater=settings.debater_model,
        controller=settings.controller_model,
        pro=settings.pro_model,
        con=settings.con_model,
    )
    return resolved


__all__ = ["ResolvedModels", "resolve_model", "resolve_models"]
