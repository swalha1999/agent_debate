"""Tests for ``agent-debate run "<topic>" --json`` (task 9.3, issue #66).

PRD §6: ``--json`` emits the :class:`DebateResult` as machine-readable JSON for
piping/parsing, and the command exits NON-ZERO on failure. These tests use
Typer's :class:`~typer.testing.CliRunner` with a stubbed
:class:`~agent_debate.core.DebateEngine` so NO network/key is required — the
``--json`` path drives the blocking :meth:`DebateEngine.run` (a single JSON blob,
no live stream).

We assert: ``--json`` prints valid JSON that parses into the DebateResult shape
(``transcript`` + ``verdict`` keys), exit code 0 on success, ONLY JSON on stdout;
a failing engine (raises) exits non-zero with the error surfaced (and not on
stdout in ``--json`` mode); the human (non-json) path also exits non-zero on
failure.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import agent_debate.cli.app as cli_app
import pytest
from agent_debate.core import DebateConfig, MissingApiKeyError, Settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict
from agent_debate.log import LogEvent
from typer.testing import CliRunner

runner = CliRunner()


def _result(topic: str) -> DebateResult:
    return DebateResult(
        topic=topic,
        verdict=Verdict(
            winner=DebateSide.PRO,
            rationale="stronger arguments",
            scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
            summary="pro won",
        ),
    )


class _BlockingEngine:
    """Stub engine whose blocking ``run`` returns a canned :class:`DebateResult`."""

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        pass

    def run(self, topic: str) -> DebateResult:
        return _result(topic)


class _FailingEngine:
    """Stub engine whose ``run``/``stream`` raise — simulates a debate failure."""

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        pass

    def run(self, topic: str) -> DebateResult:
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set")

    def stream(self, topic: str) -> Iterator[LogEvent | DebateResult]:
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set")
        yield  # pragma: no cover — generator marker; never reached.


class _CrashingEngine:
    """Stub engine whose ``run`` raises a generic (non-debate) error."""

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        pass

    def run(self, topic: str) -> DebateResult:
        raise RuntimeError("unexpected engine crash")


@pytest.fixture
def _freeze_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = Settings(rounds=7, max_words=42, search_backend="duckduckgo")
    monkeypatch.setattr(cli_app, "get_settings", lambda: fixed)


def _use(monkeypatch: pytest.MonkeyPatch, engine: type) -> None:
    monkeypatch.setattr(cli_app, "DebateEngine", engine)


def test_json_outputs_parseable_debate_result(
    monkeypatch: pytest.MonkeyPatch, _freeze_settings: None
) -> None:
    """``run --json`` prints valid JSON matching the DebateResult shape."""
    _use(monkeypatch, _BlockingEngine)
    result = runner.invoke(cli_app.app, ["run", "should we colonise mars", "--json"])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["topic"] == "should we colonise mars"
    assert "transcript" in payload
    assert "verdict" in payload
    assert payload["verdict"]["winner"] == DebateSide.PRO.value


def test_json_stdout_is_only_json(monkeypatch: pytest.MonkeyPatch, _freeze_settings: None) -> None:
    """In ``--json`` mode stdout is ONLY the JSON blob (pipeable)."""
    _use(monkeypatch, _BlockingEngine)
    result = runner.invoke(cli_app.app, ["run", "a topic", "--json"])
    assert result.exit_code == 0, result.stderr
    # The whole of stdout must parse as a single JSON document.
    json.loads(result.stdout)


def test_json_failure_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, _freeze_settings: None
) -> None:
    """A failing engine under ``--json`` exits non-zero with the error surfaced."""
    _use(monkeypatch, _FailingEngine)
    result = runner.invoke(cli_app.app, ["run", "topic", "--json"])
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.stderr


def test_human_failure_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, _freeze_settings: None
) -> None:
    """The non-json (human) path also exits non-zero on failure."""
    _use(monkeypatch, _FailingEngine)
    result = runner.invoke(cli_app.app, ["run", "topic"])
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.stderr


def test_json_generic_error_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, _freeze_settings: None
) -> None:
    """Any engine error (not just known failures) under ``--json`` exits non-zero."""
    _use(monkeypatch, _CrashingEngine)
    result = runner.invoke(cli_app.app, ["run", "topic", "--json"])
    assert result.exit_code != 0
    assert "unexpected engine crash" in result.stderr


def test_help_lists_json_flag(_freeze_settings: None) -> None:
    """``run --help`` documents the ``--json`` flag."""
    result = runner.invoke(cli_app.app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--json" in result.stdout
