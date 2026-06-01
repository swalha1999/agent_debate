"""Tests for the interactive ``menu`` command (issue #218, HW2 §8.6/§8.7).

HW2 requires the project be operable from a basic keyboard-driven terminal menu.
The menu is a thin loop over the EXISTING SDK + live renderer; these tests drive
it WITHOUT a real TTY by injecting a scripted prompt function and a FAKE runner,
so no engine / network / API key is touched (the SDK already routes real calls
through the Epic-13 gatekeeper).

We assert: the menu shows config defaults; the user can set topic / rounds /
max-words / model / search-backend; ``start`` invokes the runner with exactly
those choices and the verdict is rendered; ``quit`` exits without running;
invalid numeric input is re-prompted rather than crashing.
"""

from __future__ import annotations

from collections.abc import Iterator

import agent_debate.cli.app as cli_app
import pytest
from agent_debate.cli._menu import DebateChoices, ScriptedIO, run_menu
from agent_debate.core import Settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict
from typer.testing import CliRunner

runner = CliRunner()


def _verdict() -> Verdict:
    return Verdict(
        winner=DebateSide.PRO,
        rationale="stronger arguments",
        scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
        summary="pro won",
    )


class _FakeRunner:
    """Records the choices it was driven with and returns a canned verdict."""

    def __init__(self) -> None:
        self.calls: list[DebateChoices] = []

    def __call__(self, choices: DebateChoices) -> DebateResult:
        self.calls.append(choices)
        return DebateResult(topic=choices.topic or "", verdict=_verdict())


def _settings() -> Settings:
    return Settings(rounds=7, max_words=42, search_backend="duckduckgo")


def test_quit_without_running() -> None:
    """Choosing ``quit`` at the menu exits without invoking the runner."""
    fake = _FakeRunner()
    io = ScriptedIO(["q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    assert fake.calls == []


def test_defaults_shown() -> None:
    """The menu surfaces the config defaults (rounds/max-words/backend)."""
    fake = _FakeRunner()
    io = ScriptedIO(["q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    out = io.written()
    assert "7" in out  # configured rounds default
    assert "42" in out  # configured max_words default
    assert "duckduckgo" in out


def test_set_topic_then_start_invokes_runner() -> None:
    """Set a topic, then start: the runner is called with that topic + defaults."""
    fake = _FakeRunner()
    # 1=set topic -> "should we colonise mars"; s=start; then q=quit after result.
    io = ScriptedIO(["1", "should we colonise mars", "s", "q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    assert len(fake.calls) == 1
    choices = fake.calls[0]
    assert choices.topic == "should we colonise mars"
    assert choices.rounds == 7
    assert choices.max_words == 42
    assert choices.search_backend == "duckduckgo"
    assert "stronger arguments" in io.written()


def test_set_all_fields_then_start() -> None:
    """Each numbered option overrides the corresponding choice before starting."""
    fake = _FakeRunner()
    io = ScriptedIO(
        [
            "1",
            "a topic",
            "2",
            "3",  # rounds
            "3",
            "80",  # max words
            "4",
            "anthropic:claude-x",  # model
            "5",
            "tavily",  # search backend
            "s",
            "q",
        ]
    )
    run_menu(io=io, settings=_settings(), runner=fake)
    assert len(fake.calls) == 1
    choices = fake.calls[0]
    assert choices.topic == "a topic"
    assert choices.rounds == 3
    assert choices.max_words == 80
    assert choices.model == "anthropic:claude-x"
    assert choices.search_backend == "tavily"


def test_invalid_numeric_input_reprompts() -> None:
    """A non-numeric rounds value is rejected and re-prompted, not crashing."""
    fake = _FakeRunner()
    io = ScriptedIO(["2", "not-a-number", "5", "q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    # No run happened; the invalid value did not crash the loop.
    assert fake.calls == []
    assert "5" in io.written()


def test_non_positive_int_kept() -> None:
    """A zero/negative rounds value is rejected, keeping the current value."""
    fake = _FakeRunner()
    io = ScriptedIO(["2", "0", "q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    assert "keeping" in io.written()


def test_unknown_option_warns() -> None:
    """An unrecognised menu key warns and loops rather than crashing."""
    fake = _FakeRunner()
    io = ScriptedIO(["zzz", "q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    assert "Unknown option" in io.written()


def test_runner_returns_none_no_verdict() -> None:
    """If the runner returns no result, a 'no verdict' message is shown."""
    io = ScriptedIO(["1", "topic", "s", "q"])
    run_menu(io=io, settings=_settings(), runner=lambda _choices: None)
    assert "No verdict" in io.written()


def test_start_without_topic_is_blocked() -> None:
    """Starting with no topic set is refused (runner not called)."""
    fake = _FakeRunner()
    io = ScriptedIO(["s", "q"])
    run_menu(io=io, settings=_settings(), runner=fake)
    assert fake.calls == []


def test_menu_command_registered() -> None:
    """``agent-debate menu --help`` exists (command wired into the app)."""
    result = runner.invoke(cli_app.app, ["menu", "--help"])
    assert result.exit_code == 0


def test_menu_command_runs_with_fake_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """The ``menu`` command drives the loop with a fake engine via stdin script."""

    class _RecordingEngine:
        last_topic: str | None = None

        def __init__(self, config: object | None = None, **kwargs: object) -> None:
            pass

        def stream(self, topic: str) -> Iterator[DebateResult]:
            type(self).last_topic = topic
            yield DebateResult(topic=topic, verdict=_verdict())

    monkeypatch.setattr(cli_app, "DebateEngine", _RecordingEngine)
    monkeypatch.setattr(cli_app, "get_settings", _settings)
    # Script: set topic, start, quit.
    result = runner.invoke(
        cli_app.app,
        ["menu"],
        input="1\nclimate policy\ns\nq\n",
    )
    assert result.exit_code == 0, result.output
    assert _RecordingEngine.last_topic == "climate policy"
