"""Epic-2 acceptance tests — the config story END-TO-END (issue #25, task 2.5).

This module is the Epic-2 acceptance pass (mirroring how task 1.5 consolidated
Epic 1). It exercises the three acceptance behaviours *through the public*
:mod:`agent_debate.core` API — proving the integrated config story rather than
re-testing internals already covered by ``test_settings.py`` (2.1) /
``test_models.py`` (2.2) / ``test_validation.py`` (2.3) / ``test_model_ids.py``
(2.4):

#. **Settings loads from env** — bare PRD §7 names override the defaults and
   coerce types, and a real ``.env`` file on disk is honoured.
#. **PRO/CON fall back to DEBATER_MODEL** — including the real-world case where
   ``.env.example`` ships ``PRO_MODEL=`` (an *empty* string), and the mixed case
   where one side is overridden and the other falls back.
#. **An invalid model string fails loudly** — both a recognised-format unknown
   provider and a malformed (no-colon / blank) string raise, never returning a
   broken model, and the friendly missing-key error wins over the deep SDK one.

Every test mutates the environment via ``monkeypatch`` (and ``chdir`` for the
cwd-relative ``.env``) so nothing leaks into sibling test modules.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_debate.core import (
    MissingApiKeyError,
    Settings,
    constants,
    get_settings,
    resolve_model,
    resolve_models,
    validate_required_keys,
)

#: Every PRD §7 env var — stripped before each test so the suite never reads a
#: developer's ambient environment.
_PRD_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEBATER_MODEL",
    "CONTROLLER_MODEL",
    "PRO_MODEL",
    "CON_MODEL",
    "ROUNDS",
    "MAX_WORDS",
    "TURN_TIMEOUT_S",
    "MAX_RETRIES",
    "SEARCH_BACKEND",
    "SEARCH_API_KEY",
)


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Strip PRD §7 vars and run from a dir with no ambient ``.env``."""
    for name in _PRD_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()


# --- Acceptance 1: Settings loads from env -----------------------------------


def test_settings_loads_from_env_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public ``get_settings`` reads bare PRD §7 names and coerces types."""
    monkeypatch.setenv("ROUNDS", "3")
    monkeypatch.setenv("SEARCH_BACKEND", "tavily")
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-haiku-4-5")

    settings = get_settings()

    assert settings.rounds == 3
    assert isinstance(settings.rounds, int)
    assert settings.search_backend == "tavily"
    assert settings.debater_model == "anthropic:claude-haiku-4-5"


def test_settings_loads_from_env_file_on_disk(tmp_path: Path) -> None:
    """A real ``.env`` file in the cwd is loaded by ``Settings`` end-to-end."""
    (tmp_path / ".env").write_text("ROUNDS=8\nMAX_WORDS=42\n", encoding="utf-8")

    settings = Settings()

    assert settings.rounds == 8
    assert settings.max_words == 42


# --- Acceptance 2: PRO/CON fall back to DEBATER_MODEL -------------------------


def test_pro_con_fall_back_through_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no per-side override, resolved PRO/CON match the debater model."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-haiku-4-5")

    resolved = resolve_models(Settings())

    assert resolved.pro.model_name == resolved.debater.model_name == "claude-haiku-4-5"
    assert resolved.con.model_name == "claude-haiku-4-5"


def test_empty_string_override_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """``PRO_MODEL=`` (as shipped in ``.env.example``) falls back, not breaks.

    Copying ``.env.example`` verbatim sets ``PRO_MODEL`` to an *empty* string;
    the resolved ``pro_model`` must still be ``DEBATER_MODEL`` (empty is falsy),
    never an unusable empty model string.
    """
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.setenv("PRO_MODEL", "")
    monkeypatch.setenv("CON_MODEL", "")

    settings = Settings()

    assert settings.pro_model_override == ""  # raw value is the empty string
    assert settings.pro_model == "anthropic:claude-sonnet-4-6"  # but resolves through
    assert settings.con_model == "anthropic:claude-sonnet-4-6"


def test_mixed_pro_set_con_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """One side overridden, the other falls back — independently resolved."""
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.setenv("PRO_MODEL", "anthropic:claude-opus-4-8")

    settings = Settings()

    assert settings.pro_model == "anthropic:claude-opus-4-8"  # override wins
    assert settings.con_model == "anthropic:claude-sonnet-4-6"  # falls back


# --- Acceptance 3: an invalid model string fails loudly ----------------------


def test_unknown_provider_string_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A recognised-format but unknown provider raises, not a broken model."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")

    with pytest.raises(ValueError):
        resolve_model("not-a-real-provider:whatever")


@pytest.mark.parametrize("bad", ["", "   ", "anthropic"])
def test_malformed_model_string_raises(monkeypatch: pytest.MonkeyPatch, bad: str) -> None:
    """Blank / no-colon strings also fail loudly (a ``RuntimeError`` here)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")

    with pytest.raises((ValueError, RuntimeError)):
        resolve_model(bad)


def test_invalid_model_via_settings_fails_through_resolve_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bad ``DEBATER_MODEL`` from env surfaces loudly via ``resolve_models``."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")
    monkeypatch.setenv("DEBATER_MODEL", "not-a-real-provider:whatever")

    with pytest.raises((ValueError, RuntimeError)):
        resolve_models(Settings())


def test_missing_key_error_wins_over_sdk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Friendly missing-key error fires before any deep SDK construction error."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(MissingApiKeyError) as excinfo:
        resolve_models(Settings())

    message = str(excinfo.value)
    assert constants.PROVIDER_KEY_ENV_VARS["anthropic"] in message
    assert ".env" in message


def test_public_validate_required_keys_is_reexported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The validator is reachable from the package root and passes when keyed."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-dummy-key")

    validate_required_keys(Settings())  # must not raise
