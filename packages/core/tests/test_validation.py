"""Unit tests for startup required-key validation (issue #23, task 2.3).

TDD red-first contract: on startup the active provider's API key (e.g.
``ANTHROPIC_API_KEY`` for the default Anthropic provider) must be present. If
it is missing, :func:`validate_required_keys` raises a single, clear,
*actionable* error — naming the env var and how to fix it (see ``.env.example``)
— rather than letting a deep Pydantic AI / SDK ``UserError`` surface.

The required provider is derived from the *active* model strings
(``DEBATER_MODEL`` / ``CONTROLLER_MODEL`` / ``PRO_MODEL`` / ``CON_MODEL``): the
prefix before ``:`` selects the provider, and a provider→env-var mapping decides
which key must be set. Providers absent from the mapping are lenient (not
blocked). Every test mutates the environment via ``monkeypatch`` so it is
restored and never leaks into other test modules.
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    MissingApiKeyError,
    Settings,
    resolve_models,
    validate_required_keys,
)

#: Provider/model env vars the validator inspects (stripped before each test).
_MODEL_ENV_VARS = (
    "DEBATER_MODEL",
    "CONTROLLER_MODEL",
    "PRO_MODEL",
    "CON_MODEL",
)


@pytest.fixture(autouse=True)
def _clean_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip model env vars so each test controls the active providers."""
    for name in _MODEL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


def test_passes_when_anthropic_key_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default (Anthropic) settings validate when the key is set."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")

    # Should not raise.
    validate_required_keys(Settings())


def test_raises_when_anthropic_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing Anthropic key raises our error naming the var + a fix hint."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError) as excinfo:
        validate_required_keys(Settings())

    message = str(excinfo.value)
    assert "ANTHROPIC_API_KEY" in message
    assert ".env" in message  # actionable: how/where to fix it


def test_blank_key_is_treated_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty/whitespace key is not a valid key — it must be rejected."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")

    with pytest.raises(MissingApiKeyError):
        validate_required_keys(Settings())


def test_error_names_non_anthropic_provider_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A different active provider's missing key names *that* provider's var."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")
    monkeypatch.setenv("CONTROLLER_MODEL", "openai:gpt-5")

    with pytest.raises(MissingApiKeyError) as excinfo:
        validate_required_keys(Settings())

    assert "OPENAI_API_KEY" in str(excinfo.value)


def test_unmapped_provider_is_lenient(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider we do not map is not blocked (lenient), so no error fires."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")
    # 'mistral' has no mapped key var, so it must not raise here.
    monkeypatch.setenv("PRO_MODEL", "mistral:mistral-large")
    monkeypatch.setenv("CON_MODEL", "mistral:mistral-large")
    monkeypatch.setenv("DEBATER_MODEL", "mistral:mistral-large")
    monkeypatch.setenv("CONTROLLER_MODEL", "mistral:mistral-large")

    # Should not raise (lenient for unmapped providers).
    validate_required_keys(Settings())


def test_resolve_models_surfaces_friendly_error_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``resolve_models`` raises OUR error before the deep SDK ``UserError``."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError) as excinfo:
        resolve_models(Settings())

    assert "ANTHROPIC_API_KEY" in str(excinfo.value)


def test_lists_all_missing_vars_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Multiple distinct missing providers are reported together, deduped."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CONTROLLER_MODEL", "openai:gpt-5")

    with pytest.raises(MissingApiKeyError) as excinfo:
        validate_required_keys(Settings())

    message = str(excinfo.value)
    assert "ANTHROPIC_API_KEY" in message
    assert "OPENAI_API_KEY" in message
    # Anthropic is the debater + pro + con default; it must be deduped in the
    # reported list (named once, not three times). The list is the text between
    # the leading "...key(s): " and the first sentence-ending period.
    reported_list = message.split("key(s): ", 1)[1].split(".", 1)[0]
    assert reported_list.count("ANTHROPIC_API_KEY") == 1
