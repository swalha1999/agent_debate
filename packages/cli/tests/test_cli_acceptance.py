"""Epic-9 acceptance tests — the CLI story END-TO-END (task 9.4, issue #67).

This module is the Epic-9 acceptance/consolidation pass (mirroring how earlier
epics consolidated in a ``*_acceptance`` module). It exercises the headline CLI
behaviours THROUGH the public Typer app via :class:`~typer.testing.CliRunner`
against a MOCKED engine (stubs in :mod:`._acceptance_helpers`) — NO network / API
key — proving the integrated story that the CLI is a thin, correct driver of the
SDK rather than re-testing internals already covered by the per-task suites
(``test_cli_run.py`` 9.1 / ``test_cli_live.py`` 9.2 / ``test_cli_json.py`` 9.3):

#. ``run "<topic>"`` runs a mocked debate and PRINTS the full TRANSCRIPT (Pro +
   Con messages) AND the VERDICT (the human/live path).
#. ``--json`` prints a machine-readable :class:`DebateResult` JSON that parses.
#. EXIT CODES are correct: 0 on success, non-zero on failure for BOTH paths.
#. The option flags (``--rounds`` / ``--max-words`` / ``--model`` /
   ``--search-backend``) reach the engine config.
#. ``--help`` lists the ``run`` command + its options.
"""

from __future__ import annotations

import json

import agent_debate.cli.app as cli_app
import pytest
from _acceptance_helpers import (
    CON_TEXT,
    FIXED_MAX_WORDS,
    FIXED_ROUNDS,
    PRO_TEXT,
    VERDICT_RATIONALE,
    FailingEngine,
    RecordingEngine,
    patch_engine,  # noqa: F401 — autouse fixture imported for pytest discovery.
)
from typer.testing import CliRunner

runner = CliRunner()


def _use_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_app, "DebateEngine", FailingEngine)


# --- Acceptance 1: run prints the full transcript + verdict (human path) ------


def test_run_prints_transcript_and_verdict_end_to_end() -> None:
    """``run "<topic>"`` renders BOTH debater messages AND the verdict, in order."""
    result = runner.invoke(cli_app.app, ["run", "should we colonise mars"])
    assert result.exit_code == 0, result.output
    out = result.output
    assert PRO_TEXT in out
    assert CON_TEXT in out
    assert VERDICT_RATIONALE in out
    assert "Verdict" in out
    # Transcript precedes the verdict (the live render order).
    assert out.index(CON_TEXT) < out.index("Verdict")


# --- Acceptance 2: --json prints a parseable DebateResult ---------------------


def test_json_prints_parseable_debate_result() -> None:
    """``run "<topic>" --json`` emits a single JSON blob matching DebateResult."""
    result = runner.invoke(cli_app.app, ["run", "a topic", "--json"])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["topic"] == "a topic"
    assert "transcript" in payload and "verdict" in payload


# --- Acceptance 3: exit codes are correct for BOTH paths ----------------------


def test_human_path_fails_non_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing engine on the human path exits non-zero with the error on stderr."""
    _use_failing(monkeypatch)
    result = runner.invoke(cli_app.app, ["run", "topic"])
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.stderr


def test_json_path_fails_non_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing engine under ``--json`` exits non-zero with clean stdout."""
    _use_failing(monkeypatch)
    result = runner.invoke(cli_app.app, ["run", "topic", "--json"])
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.stderr
    assert result.stdout.strip() == ""  # no partial JSON on failure


def test_invalid_option_exits_non_zero() -> None:
    """An invalid ``--rounds`` (config validation) is rejected with exit != 0."""
    result = runner.invoke(cli_app.app, ["run", "topic", "--rounds", "0"])
    assert result.exit_code != 0


# --- Acceptance 4: option flags reach the engine config -----------------------


def test_flags_reach_engine_config(patch_engine: type[RecordingEngine]) -> None:  # noqa: F811
    """``--rounds`` / ``--max-words`` / ``--model`` / ``--search-backend`` apply."""
    result = runner.invoke(
        cli_app.app,
        [
            "run",
            "t",
            "--rounds",
            "3",
            "--max-words",
            "80",
            "--model",
            "anthropic:claude-x",
            "--search-backend",
            "tavily",
        ],
    )
    assert result.exit_code == 0, result.output
    config = patch_engine.last_config
    assert config is not None
    assert (config.rounds, config.max_words) == (3, 80)
    assert config.pro_model == config.con_model == "anthropic:claude-x"
    assert patch_engine.last_settings is not None
    assert patch_engine.last_settings.search_backend == "tavily"


def test_bare_run_uses_config_defaults(patch_engine: type[RecordingEngine]) -> None:  # noqa: F811
    """With no flags the config defaults come from Settings, not the CLI."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    assert result.exit_code == 0, result.output
    config = patch_engine.last_config
    assert config is not None
    assert (config.rounds, config.max_words) == (FIXED_ROUNDS, FIXED_MAX_WORDS)


# --- Acceptance 5: --help lists the command + options -------------------------


def test_help_lists_command_and_options() -> None:
    """``--help`` lists ``run``; ``run --help`` lists every option + ``--json``."""
    top = runner.invoke(cli_app.app, ["--help"])
    assert top.exit_code == 0
    assert "run" in top.output
    sub = runner.invoke(cli_app.app, ["run", "--help"])
    assert sub.exit_code == 0
    for token in ("--rounds", "--max-words", "--model", "--search-backend", "--json"):
        assert token in sub.output
