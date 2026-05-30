"""Unit tests for the ``agent_debate.core`` model resolver (issue #22, task 2.2).

TDD red-first contract: a resolver maps the PRD §7 ``DEBATER_MODEL`` /
``CONTROLLER_MODEL`` / ``PRO_MODEL`` / ``CON_MODEL`` strings to Pydantic AI
model objects, honouring the PRO/CON → DEBATER fallback, with Anthropic the
default provider. Swapping providers must be a config-only change: an env var
flip changes the resolved model with **zero code changes**.

No network call is made — :func:`resolve_model` only *constructs* a model
object (actual API calls route through the Epic 13 gatekeeper later). The
Anthropic client reads ``ANTHROPIC_API_KEY`` at construction, so a dummy key is
injected via ``monkeypatch`` so the suite never needs a real key.
"""

from __future__ import annotations

import pytest
from agent_debate.core import ResolvedModels, Settings, resolve_model, resolve_models

#: PRD §7 model env vars the resolver consumes (stripped before each test).
_MODEL_ENV_VARS = (
    "DEBATER_MODEL",
    "CONTROLLER_MODEL",
    "PRO_MODEL",
    "CON_MODEL",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip model env vars and inject a dummy key so construction never fails.

    The Anthropic provider reads ``ANTHROPIC_API_KEY`` when the model is built;
    a fake value lets the object construct without a real key or any network
    call.
    """
    for name in _MODEL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")


def test_resolve_model_returns_anthropic_for_default_string() -> None:
    """A bare ``provider:model`` string resolves to the matching provider."""
    model = resolve_model("anthropic:claude-sonnet-4-6")

    assert model.system == "anthropic"
    assert model.model_name == "claude-sonnet-4-6"


def test_resolve_models_defaults_match_prd_section_7() -> None:
    """Default settings → debater=sonnet, controller=opus (PRD §7), anthropic."""
    resolved = resolve_models(Settings())

    assert isinstance(resolved, ResolvedModels)
    assert resolved.debater.system == "anthropic"
    assert resolved.debater.model_name == "claude-sonnet-4-6"
    assert resolved.controller.system == "anthropic"
    assert resolved.controller.model_name == "claude-opus-4-8"


def test_env_swaps_debater_with_zero_code_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flipping ``DEBATER_MODEL`` changes the resolved debater — no code edit."""
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-haiku-4-5")

    resolved = resolve_models(Settings())

    assert resolved.debater.model_name == "claude-haiku-4-5"


def test_pro_con_fall_back_to_debater_when_unset() -> None:
    """Unset PRO/CON overrides resolve to the same model as the debater."""
    resolved = resolve_models(Settings())

    assert resolved.pro.system == resolved.debater.system
    assert resolved.pro.model_name == resolved.debater.model_name
    assert resolved.con.model_name == resolved.debater.model_name


def test_pro_con_overrides_take_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set PRO/CON overrides win over ``DEBATER_MODEL`` (cross-provider)."""
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.setenv("PRO_MODEL", "anthropic:claude-opus-4-8")
    monkeypatch.setenv("CON_MODEL", "anthropic:claude-haiku-4-5")

    resolved = resolve_models(Settings())

    assert resolved.pro.model_name == "claude-opus-4-8"
    assert resolved.con.model_name == "claude-haiku-4-5"
    assert resolved.debater.model_name == "claude-sonnet-4-6"


def test_bad_model_string_raises_clearly() -> None:
    """A clearly invalid provider fails loudly, not with a broken model."""
    with pytest.raises(ValueError):
        resolve_model("not-a-real-provider:whatever")
