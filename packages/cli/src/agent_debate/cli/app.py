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

import typer
from agent_debate.cli._render import render_result
from agent_debate.core import DebateConfig, DebateEngine, Settings, get_settings
from agent_debate.log import get_logger

app = typer.Typer(
    name="agent-debate",
    help="Run a structured multi-agent debate from the terminal (PRD §6).",
    no_args_is_help=True,
    add_completion=False,
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
) -> None:
    """Run a full debate on TOPIC and print the transcript + verdict."""
    settings = _resolve_settings(rounds, max_words, model, search_backend)
    try:
        config = DebateConfig.from_settings(settings)
    except ValueError as exc:  # invalid option (e.g. rounds <= 0)
        raise typer.BadParameter(str(exc)) from exc
    _LOG.info("cli_run_start", topic=topic, rounds=config.rounds, max_words=config.max_words)
    engine = DebateEngine(config, settings=settings)
    result = engine.run(topic)
    typer.echo(render_result(result))


__all__ = ["app", "run"]
