"""Tests for the Typer ``run`` command (task 9.1, issue #64).

The CLI is a thin shell over the SDK (PRD §6): ``agent-debate run "<topic>"``
builds a :class:`DebateConfig` from :class:`Settings` (overridden by the options
the user passed) and drives :class:`DebateEngine`. These tests use Typer's
:class:`~typer.testing.CliRunner` and replace the engine with a recording stub so
NO network call / API key is needed — the SDK already routes real calls through
the Epic-13 gatekeeper.

We assert: ``--help`` lists every option; a bare ``run`` invokes the engine with a
config whose defaults come from ``Settings``; each option (``--rounds``,
``--max-words``, ``--model``, ``--search-backend``) overrides the derived config;
the transcript + verdict are printed; and invalid input is rejected.
"""

from __future__ import annotations

from collections.abc import Iterator

import agent_debate.cli.app as cli_app
import pytest
from agent_debate.core import DebateConfig, Settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict
from agent_debate.log import LogEvent
from typer.testing import CliRunner

runner = CliRunner()


class _RecordingEngine:
    """Stand-in for :class:`DebateEngine` that records its config + topic.

    The ``run`` command now consumes :meth:`DebateEngine.stream` (live render,
    task 9.2), so the stub yields a canned event sequence (a Pro message + the
    verdict) ending with the final :class:`DebateResult` — no network/key needed.
    """

    last_config: DebateConfig | None = None
    last_topic: str | None = None
    last_settings: Settings | None = None

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        type(self).last_config = config
        type(self).last_settings = kwargs.get("settings")  # type: ignore[assignment]

    def stream(self, topic: str) -> Iterator[LogEvent | DebateResult]:
        type(self).last_topic = topic
        yield LogEvent(
            run_id="r",
            round=1,
            agent=DebateSide.PRO.value,
            event_type="message",
            payload={"content": "hello world", "word_count": 2},
        )
        yield LogEvent(
            run_id="r",
            round=0,
            agent="controller",
            event_type="verdict",
            payload={
                "winner": DebateSide.PRO.value,
                "summary": "pro won",
                "rationale": "stronger arguments",
            },
        )
        yield DebateResult(
            topic=topic,
            verdict=Verdict(
                winner=DebateSide.PRO,
                rationale="stronger arguments",
                scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
                summary="pro won",
            ),
        )


@pytest.fixture(autouse=True)
def _patch_engine(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingEngine]:
    """Replace the engine + freeze a known ``Settings`` so no network/key is used."""
    _RecordingEngine.last_config = None
    _RecordingEngine.last_topic = None
    _RecordingEngine.last_settings = None
    monkeypatch.setattr(cli_app, "DebateEngine", _RecordingEngine)
    fixed = Settings(rounds=7, max_words=42, search_backend="duckduckgo")
    monkeypatch.setattr(cli_app, "get_settings", lambda: fixed)
    return _RecordingEngine


def test_help_lists_run_options() -> None:
    """``run --help`` documents the topic + every option (plain Click help)."""
    result = runner.invoke(cli_app.app, ["run", "--help"])
    assert result.exit_code == 0
    for token in ("--rounds", "--max-words", "--model", "--search-backend"):
        assert token in result.output


def test_run_uses_settings_defaults() -> None:
    """A bare ``run`` derives the config defaults from ``Settings``."""
    result = runner.invoke(cli_app.app, ["run", "should we colonise mars"])
    assert result.exit_code == 0, result.output
    config = _RecordingEngine.last_config
    assert config is not None
    assert config.rounds == 7
    assert config.max_words == 42
    assert _RecordingEngine.last_topic == "should we colonise mars"


def test_options_override_config() -> None:
    """Each option overrides the derived config; ``--model`` sets the debater model."""
    result = runner.invoke(
        cli_app.app,
        [
            "run",
            "topic",
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
    config = _RecordingEngine.last_config
    assert config is not None
    assert config.rounds == 3
    assert config.max_words == 80
    assert config.debater_model == "anthropic:claude-x"
    assert config.pro_model == "anthropic:claude-x"
    assert config.con_model == "anthropic:claude-x"
    assert _RecordingEngine.last_settings is not None
    assert _RecordingEngine.last_settings.search_backend == "tavily"


def test_run_prints_transcript_and_verdict() -> None:
    """The command prints the transcript content and the verdict."""
    result = runner.invoke(cli_app.app, ["run", "a topic"])
    assert result.exit_code == 0, result.output
    assert "hello world" in result.output
    assert "pro" in result.output.lower()
    assert "stronger arguments" in result.output


def test_invalid_rounds_rejected() -> None:
    """A non-positive ``--rounds`` is rejected (config validation, exit != 0)."""
    result = runner.invoke(cli_app.app, ["run", "topic", "--rounds", "0"])
    assert result.exit_code != 0


def test_missing_topic_errors() -> None:
    """Calling ``run`` with no topic is a usage error."""
    result = runner.invoke(cli_app.app, ["run"])
    assert result.exit_code != 0
