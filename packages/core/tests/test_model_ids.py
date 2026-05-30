"""Pinning tests for the Anthropic model IDs (issue #24 / task 2.4).

These tests *pin* the exact, confirmed Anthropic model IDs used as the
``DEBATER_MODEL`` / ``CONTROLLER_MODEL`` defaults so accidental drift (a typo,
a bumped suffix, a stray rename) is caught loudly in CI rather than surfacing
as a confusing provider error at runtime.

The IDs live once as the ``DEFAULT_*`` literals in
:mod:`agent_debate.core.constants` (the single source of truth, PRD §7.2) and
are mirrored in ``.env.example`` for humans. This module asserts that the three
representations agree:

* the ``constants.DEFAULT_*`` literals equal the confirmed, current IDs;
* the ``Settings`` defaults equal those constants;
* ``.env.example`` documents the same IDs.

It also confirms each default string is *constructible* via
:func:`resolve_model` offline (a dummy ``ANTHROPIC_API_KEY`` is injected so no
network/API call is made and construction never raises on a missing key).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from agent_debate.core import Settings
from agent_debate.core import constants as core_constants
from agent_debate.core.models import resolve_model

#: The confirmed, current Anthropic model IDs in pydantic-ai ``provider:model``
#: form (the part after ``anthropic:`` is the raw Anthropic model ID).
PINNED_DEBATER_MODEL = "anthropic:claude-sonnet-4-6"
PINNED_CONTROLLER_MODEL = "anthropic:claude-opus-4-8"

#: A valid, current alternative for cost-sensitive debaters (documented in
#: ``.env.example``); pinned so its ID cannot silently drift either.
PINNED_HAIKU_MODEL = "anthropic:claude-haiku-4-5-20251001"

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def test_constants_pin_confirmed_anthropic_ids() -> None:
    """The ``DEFAULT_*`` constants equal the confirmed Anthropic IDs."""
    assert core_constants.DEFAULT_DEBATER_MODEL == PINNED_DEBATER_MODEL
    assert core_constants.DEFAULT_CONTROLLER_MODEL == PINNED_CONTROLLER_MODEL


def test_pinned_ids_are_well_formed() -> None:
    """Each pinned ID is a well-formed ``anthropic:claude-...`` string."""
    for model_id in (
        PINNED_DEBATER_MODEL,
        PINNED_CONTROLLER_MODEL,
        PINNED_HAIKU_MODEL,
    ):
        provider, _, name = model_id.partition(":")
        assert provider == "anthropic"
        assert name.startswith("claude-")


def test_settings_defaults_match_pinned_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``Settings`` defaults resolve to the pinned IDs with no env set."""
    for name in ("DEBATER_MODEL", "CONTROLLER_MODEL"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    # Isolate from any ambient ``.env`` (default ``env_file`` is cwd-relative).
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    assert settings.debater_model == PINNED_DEBATER_MODEL
    assert settings.controller_model == PINNED_CONTROLLER_MODEL


def test_env_example_documents_pinned_ids() -> None:
    """``.env.example`` documents the same pinned debater/controller IDs."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert f"DEBATER_MODEL={PINNED_DEBATER_MODEL}" in text
    assert f"CONTROLLER_MODEL={PINNED_CONTROLLER_MODEL}" in text
    # The Haiku alternative is mentioned (as a comment) so operators know the
    # exact cost-sensitive ID without guessing.
    assert PINNED_HAIKU_MODEL in text


def test_default_models_resolve_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each default model string constructs via ``resolve_model`` offline.

    A dummy key is injected so eager Anthropic client construction does not
    raise on a missing ``ANTHROPIC_API_KEY``; no network call is made.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-test-token")

    for model_id in (PINNED_DEBATER_MODEL, PINNED_CONTROLLER_MODEL):
        model = resolve_model(model_id)
        assert model is not None
