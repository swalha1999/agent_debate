"""Unit tests for the ``agent_debate.core`` Settings model (issue #21, PRD §7).

TDD red-first contract for task 2.1: ``Settings`` loads every PRD §7 field
from the environment / ``.env`` with defaults that match §7 exactly, coerces
types (``ROUNDS`` is an ``int``), and resolves the per-side ``PRO_MODEL`` /
``CON_MODEL`` overrides — falling back to ``DEBATER_MODEL`` when unset.

Each test injects env via ``monkeypatch`` so the suite never needs a real
``ANTHROPIC_API_KEY`` and never reads a developer's ambient environment.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from agent_debate.core import Settings, get_settings

#: PRD §7 environment variable names that the model must consume.
PRD_ENV_VARS = (
    "ANTHROPIC_API_KEY",
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
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Strip every PRD §7 var and run from a dir with no ambient ``.env``."""
    for name in PRD_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    # Default ``env_file=".env"`` is resolved relative to the cwd; isolate it.
    monkeypatch.chdir(tmp_path)


def test_defaults_match_prd_section_7() -> None:
    """With no env set, every default equals the PRD §7 table."""
    settings = Settings()

    assert settings.anthropic_api_key is None
    assert settings.debater_model == "anthropic:claude-sonnet-4-6"
    assert settings.controller_model == "anthropic:claude-opus-4-8"
    assert settings.pro_model_override is None
    assert settings.con_model_override is None
    assert settings.rounds == 10
    assert settings.max_words == 150
    assert settings.turn_timeout_s == 60
    assert settings.max_retries == 2
    assert settings.search_backend == "duckduckgo"
    assert settings.search_api_key is None


def test_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bare-named env vars (no prefix) override defaults and coerce types."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-test-token")
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-haiku-4-5")
    monkeypatch.setenv("CONTROLLER_MODEL", "openai:gpt-5")
    monkeypatch.setenv("ROUNDS", "3")
    monkeypatch.setenv("MAX_WORDS", "75")
    monkeypatch.setenv("TURN_TIMEOUT_S", "30")
    monkeypatch.setenv("MAX_RETRIES", "5")
    monkeypatch.setenv("SEARCH_BACKEND", "tavily")
    monkeypatch.setenv("SEARCH_API_KEY", "tvly-dummy")

    settings = Settings()

    assert settings.anthropic_api_key == "dummy-test-token"
    assert settings.debater_model == "anthropic:claude-haiku-4-5"
    assert settings.controller_model == "openai:gpt-5"
    assert settings.rounds == 3
    assert isinstance(settings.rounds, int)
    assert settings.max_words == 75
    assert settings.turn_timeout_s == 30
    assert settings.max_retries == 5
    assert settings.search_backend == "tavily"
    assert settings.search_api_key == "tvly-dummy"


def test_case_insensitive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lower-cased env names resolve too (case_sensitive=False)."""
    monkeypatch.setenv("rounds", "7")

    assert Settings().rounds == 7


def test_pro_con_fall_back_to_debater_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset per-side overrides resolve to ``DEBATER_MODEL``."""
    monkeypatch.setenv("DEBATER_MODEL", "openai:gpt-5")
    settings = Settings()

    assert settings.pro_model == "openai:gpt-5"
    assert settings.con_model == "openai:gpt-5"


def test_pro_con_overrides_take_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set per-side overrides win over ``DEBATER_MODEL``."""
    monkeypatch.setenv("DEBATER_MODEL", "anthropic:claude-sonnet-4-6")
    monkeypatch.setenv("PRO_MODEL", "openai:gpt-5")
    monkeypatch.setenv("CON_MODEL", "google:gemini-2.5")

    settings = Settings()

    assert settings.pro_model == "openai:gpt-5"
    assert settings.con_model == "google:gemini-2.5"
    assert settings.debater_model == "anthropic:claude-sonnet-4-6"


def test_loads_from_dotenv_file(tmp_path: Path) -> None:
    """Values come from a ``.env`` file in the cwd when present.

    The autouse ``_clean_env`` fixture ``chdir``-s to this same ``tmp_path``,
    so a ``.env`` written here is the one the default ``env_file=".env"`` loads.
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_API_KEY=dummy-from-dotenv\nROUNDS=4\nSEARCH_BACKEND=bing\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.anthropic_api_key == "dummy-from-dotenv"
    assert settings.rounds == 4
    assert settings.search_backend == "bing"


def test_unknown_env_vars_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extra env vars do not raise (extra='ignore')."""
    monkeypatch.setenv("SOME_UNRELATED_VAR", "value")

    assert Settings().rounds == 10


def test_invalid_int_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-numeric ``ROUNDS`` is a validation error, not a silent pass."""
    monkeypatch.setenv("ROUNDS", "not-a-number")
    with pytest.raises(ValueError):
        Settings()


def test_get_settings_returns_cached_singleton() -> None:
    """``get_settings`` returns a cached ``Settings`` instance."""
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()

    assert isinstance(first, Settings)
    assert first is second
    get_settings.cache_clear()


def test_get_settings_exports_anthropic_key_to_os_environ(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``get_settings()`` sets ``ANTHROPIC_API_KEY`` in ``os.environ`` from ``.env``.

    Downstream libraries (pydantic-ai Anthropic provider) read ``os.environ``
    directly; this ensures the key is visible even when only in ``.env``.
    """
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    get_settings.cache_clear()

    assert settings.anthropic_api_key == "sk-from-dotenv"
    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-from-dotenv"


def test_get_settings_does_not_overwrite_existing_anthropic_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``get_settings()`` does NOT overwrite a shell-set ``ANTHROPIC_API_KEY``.

    An explicit shell override must take precedence over the ``.env`` value.
    """
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-shell")
    get_settings.cache_clear()
    get_settings()
    get_settings.cache_clear()

    assert os.environ.get("ANTHROPIC_API_KEY") == "sk-from-shell"


def test_get_settings_exports_search_api_key_to_os_environ(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``get_settings()`` sets ``SEARCH_API_KEY`` in ``os.environ`` from ``.env``."""
    (tmp_path / ".env").write_text("SEARCH_API_KEY=tvly-from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    get_settings.cache_clear()

    assert settings.search_api_key == "tvly-from-dotenv"
    assert os.environ.get("SEARCH_API_KEY") == "tvly-from-dotenv"


def test_get_settings_does_not_export_none_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``get_settings()`` does not inject ``None`` API keys into ``os.environ``."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SEARCH_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    get_settings.cache_clear()

    assert settings.anthropic_api_key is None
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert settings.search_api_key is None
    assert "SEARCH_API_KEY" not in os.environ
