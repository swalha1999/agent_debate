"""Typer CLI app — ``agent-debate run "<topic>"`` (task 9.1, issue #64).

PRD §6: a thin Typer shell over the SDK. The ``run`` command takes a topic plus
``--rounds`` / ``--max-words`` / ``--model`` / ``--search-backend`` and drives
:class:`~agent_debate.core.DebateEngine`.

No hard-coded values: every option DEFAULTS to ``None`` and only the flags the
user actually passed override the process :class:`~agent_debate.core.Settings`
(loaded via :func:`get_settings`). A :class:`~agent_debate.core.DebateConfig` is
then derived from those settings, so changing config — not the CLI — changes the
defaults. ``--model`` sets the debater model (resolving both PRO/CON sides);
``--search-backend`` selects the search plug-in; ``--rounds``/``--max-words``
override the per-run loop budget.

Real runs need ``ANTHROPIC_API_KEY`` (validated in the SDK) and route every model
call through the Epic-13 gatekeeper; tests inject a stub engine so no network or
key is required.
"""

from __future__ import annotations

from typing import NamedTuple

import typer
from agent_debate.cli._json import clean_stdout, emit_json, run_or_fail
from agent_debate.cli._live import render_stream
from agent_debate.cli._menu import DebateChoices, run_menu
from agent_debate.core import DebateConfig, DebateEngine, Settings, get_settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.log import get_logger

app = typer.Typer(
    name="agent-debate",
    help="Run a structured multi-agent debate from the terminal (PRD §6).",
    no_args_is_help=True,
    add_completion=False,
    # Plain Click help (no rich panels): rich wraps long option names like
    # ``--search-backend`` across its help box at narrow terminal widths, which
    # is brittle to assert on and to read in piped/CI output.
    rich_markup_mode=None,
)

_LOG = get_logger("cli")


@app.callback()
def _main() -> None:
    """agent-debate — drive a structured multi-agent debate (PRD §6).

    A no-op group callback so the app stays multi-command (``agent-debate run
    …``) rather than collapsing into a single implicit command; future
    subcommands (watch/replay) hang off the same group.
    """


def _resolve_settings(
    rounds: int | None,
    max_words: int | None,
    model: str | None,
    search_backend: str | None,
) -> Settings:
    """Return process settings with only the user-supplied options overridden.

    Options left as ``None`` keep their configured value, so the CLI carries no
    hard-coded defaults — they all come from :class:`Settings` / config.
    """
    base = get_settings()
    overrides: dict[str, object] = {}
    if rounds is not None:
        overrides["rounds"] = rounds
    if max_words is not None:
        overrides["max_words"] = max_words
    if model is not None:
        overrides["debater_model"] = model
    if search_backend is not None:
        overrides["search_backend"] = search_backend
    return base.model_copy(update=overrides) if overrides else base


@app.command()
def run(
    topic: str = typer.Argument(..., help="The debate topic to argue."),
    rounds: int | None = typer.Option(None, "--rounds", help="Debate rounds per side."),
    max_words: int | None = typer.Option(
        None, "--max-words", help="Word limit per debate message."
    ),
    model: str | None = typer.Option(
        None, "--model", help="`provider:model` override for the debaters."
    ),
    search_backend: str | None = typer.Option(
        None, "--search-backend", help="Search backend plug-in (e.g. duckduckgo/tavily)."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit the DebateResult as machine-readable JSON (no live UI)."
    ),
) -> None:
    """Run a full debate on TOPIC, rendering the LIVE transcript + verdict.

    Without ``--json`` (the human view), consumes :meth:`DebateEngine.stream` and
    renders each event LIVE via Rich (Pro/Con messages per round, inline
    controller nudges, the final verdict) as it arrives. With ``--json``, drives
    the blocking :meth:`DebateEngine.run` and prints ONLY the
    :class:`DebateResult` as a single machine-readable JSON blob on stdout so it
    is pipeable/parseable.

    On failure (missing key, invalid topic, a turn exhausting its retries, or any
    engine error) BOTH paths report to stderr and exit non-zero
    (:data:`~agent_debate.cli._json.EXIT_FAILURE`).
    """
    opts = _Options(rounds, max_words, model, search_backend)
    if json_output:
        _run_json(topic, opts)
    else:
        _run_human(topic, opts)


class _Options(NamedTuple):
    """The user-supplied ``run`` options that override the configured defaults."""

    rounds: int | None
    max_words: int | None
    model: str | None
    search_backend: str | None


def _prepare(topic: str, opts: _Options) -> DebateEngine:
    """Resolve settings, build the config (logging the start), and the engine."""
    settings = _resolve_settings(opts.rounds, opts.max_words, opts.model, opts.search_backend)
    try:
        config = DebateConfig.from_settings(settings)
    except ValueError as exc:  # invalid option (e.g. rounds <= 0)
        raise typer.BadParameter(str(exc)) from exc
    _LOG.info("cli_run_start", topic=topic, rounds=config.rounds, max_words=config.max_words)
    return DebateEngine(config, settings=settings)


def _run_json(topic: str, opts: _Options) -> None:
    """``--json`` path: emit ONLY the DebateResult JSON on stdout (logs to stderr).

    The whole preparation + blocking run happens under :func:`clean_stdout`, so
    every LOG console line (settings load, run start, engine events) goes to
    stderr and stdout carries just the single JSON blob.
    """
    with clean_stdout():
        engine = _prepare(topic, opts)
        result = run_or_fail(lambda: engine.run(topic), log=_LOG)
    emit_json(result)


def _run_human(topic: str, opts: _Options) -> None:
    """Default path: render the LIVE transcript via Rich, exit non-zero on error."""
    engine = _prepare(topic, opts)
    run_or_fail(lambda: render_stream(topic, engine.stream(topic)), log=_LOG)


class _TyperIO:
    """Real keyboard-driven I/O for the menu (Typer prompts + echo, no new dep)."""

    def prompt(self, text: str) -> str:
        """Read one line from the user via Typer's built-in prompt."""
        return str(typer.prompt(text, default="", show_default=False))

    def echo(self, text: str) -> None:
        """Write one line to stdout via Typer's echo."""
        typer.echo(text)


def _menu_runner(choices: DebateChoices) -> DebateResult | None:
    """Reuse the existing SDK path: stream the live transcript for ``choices``."""
    assert choices.topic is not None  # menu refuses to start without a topic
    opts = _Options(choices.rounds, choices.max_words, choices.model, choices.search_backend)
    engine = _prepare(choices.topic, opts)
    return run_or_fail(
        lambda: render_stream(choices.topic or "", engine.stream(choices.topic or "")),
        log=_LOG,
    )


@app.command()
def menu() -> None:
    """Drive a debate from an interactive, keyboard-driven terminal MENU (HW2 §8.6).

    Launches a numbered menu where the user sets the topic / rounds / max-words /
    model / search-backend (config defaults shown), then ``start`` runs the debate
    through the SAME SDK + live renderer the ``run`` command uses, prints the live
    transcript, and shows the verdict. ``quit`` exits. No debate logic is
    duplicated; defaults come from :class:`Settings`.
    """
    run_menu(io=_TyperIO(), settings=get_settings(), runner=_menu_runner)


__all__ = ["app", "menu", "run"]
