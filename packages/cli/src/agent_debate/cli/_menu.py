"""Interactive keyboard-driven terminal menu (issue #218, HW2 §8.6/§8.7).

HW2 requires the project be operable from a BASIC keyboard-driven terminal menu,
alongside the existing arg-based ``run`` command. This module is a thin loop over
the SAME SDK + live renderer the ``run`` command uses — it does NOT duplicate any
debate logic. The user picks the topic / rounds / max-words / model / search
backend (config defaults shown), then ``start`` runs the debate (streaming the
live transcript) and the verdict is rendered.

All I/O is injected through the :class:`MenuIO` protocol (a ``prompt`` + ``echo``
pair) and the debate is driven by an injected ``runner`` callable, so the whole
flow is unit-testable with scripted input and a fake runner — no real TTY, engine
or API key. The real wiring (Typer prompts + a DebateEngine runner) lives in
:mod:`agent_debate.cli.app`; defaults come from :class:`Settings`, never hard-coded.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple, Protocol

from agent_debate.cli._live_style import side_label
from agent_debate.log import get_logger

if TYPE_CHECKING:
    from agent_debate.core import Settings
    from agent_debate.core.engine.result import DebateResult

_LOG = get_logger("cli.menu")


class DebateChoices(NamedTuple):
    """The user-selected debate parameters collected by the menu loop."""

    topic: str | None
    rounds: int
    max_words: int
    model: str | None
    search_backend: str


#: A debate runner: takes the chosen parameters and returns the final result.
DebateRunner = Callable[[DebateChoices], "DebateResult | None"]


class MenuIO(Protocol):
    """Injectable terminal I/O so the menu is testable without a real TTY."""

    def prompt(self, text: str) -> str:
        """Return one line of user input for ``text`` (keyboard-driven)."""

    def echo(self, text: str) -> None:
        """Write one line of output to the user."""


class ScriptedIO:
    """A :class:`MenuIO` driven by a fixed list of inputs (for tests/non-TTY)."""

    def __init__(self, inputs: list[str]) -> None:
        self._inputs = list(inputs)
        self._out: list[str] = []

    def prompt(self, text: str) -> str:
        self._out.append(text)
        return self._inputs.pop(0) if self._inputs else "q"

    def echo(self, text: str) -> None:
        self._out.append(text)

    def written(self) -> str:
        """Return everything echoed/prompted so far, for assertions."""
        return "\n".join(self._out)


def _menu_text(choices: DebateChoices) -> str:
    """Render the numbered menu showing the current/selected values."""
    topic = choices.topic or "(not set)"
    return (
        "\n=== agent-debate menu ===\n"
        f"  current topic : {topic}\n"
        "  1) set topic\n"
        f"  2) set rounds       (current: {choices.rounds})\n"
        f"  3) set max words    (current: {choices.max_words})\n"
        f"  4) set model        (current: {choices.model or 'config default'})\n"
        f"  5) set search       (current: {choices.search_backend})\n"
        "  s) start debate\n"
        "  q) quit"
    )


def _set_int(io: MenuIO, label: str, current: int) -> int:
    """Prompt for a positive integer; keep ``current`` on invalid input."""
    raw = io.prompt(f"Enter {label}").strip()
    try:
        value = int(raw)
    except ValueError:
        io.echo(f"Invalid {label!r}: {raw!r} is not a number — keeping {current}.")
        return current
    if value <= 0:
        io.echo(f"Invalid {label!r}: must be positive — keeping {current}.")
        return current
    return value


def _render_verdict(io: MenuIO, result: DebateResult | None) -> None:
    """Echo a concise verdict summary after a debate completes."""
    if result is None or result.verdict is None:
        io.echo("No verdict was produced.")
        return
    verdict = result.verdict
    io.echo(
        f"Verdict — winner: {side_label(verdict.winner.value)} | "
        f"{verdict.summary}\nRationale: {verdict.rationale}"
    )


def _start(io: MenuIO, choices: DebateChoices, runner: DebateRunner) -> None:
    """Run the debate via the injected runner, or refuse if no topic is set."""
    if not choices.topic:
        io.echo("Set a topic first (option 1) before starting.")
        return
    _LOG.info("menu_start", topic=choices.topic, rounds=choices.rounds)
    result = runner(choices)
    _render_verdict(io, result)


def initial_choices(settings: Settings) -> DebateChoices:
    """Build the starting choices from config defaults (no hard-coded values)."""
    return DebateChoices(
        topic=None,
        rounds=settings.rounds,
        max_words=settings.max_words,
        model=None,
        search_backend=settings.search_backend,
    )


def run_menu(*, io: MenuIO, settings: Settings, runner: DebateRunner) -> None:
    """Drive the interactive keyboard menu loop until the user quits.

    Reuses the SDK through the injected ``runner`` (the app wires the real
    DebateEngine + live renderer); defaults come from ``settings``.
    """
    choices = initial_choices(settings)
    while True:
        io.echo(_menu_text(choices))
        action = io.prompt("Select an option").strip().lower()
        if action == "q":
            io.echo("Goodbye.")
            return
        if action == "1":
            choices = choices._replace(topic=io.prompt("Enter topic").strip() or None)
        elif action == "2":
            choices = choices._replace(rounds=_set_int(io, "rounds", choices.rounds))
        elif action == "3":
            choices = choices._replace(max_words=_set_int(io, "max words", choices.max_words))
        elif action == "4":
            choices = choices._replace(model=io.prompt("Enter model").strip() or None)
        elif action == "5":
            choices = choices._replace(
                search_backend=io.prompt("Enter search backend").strip() or choices.search_backend
            )
        elif action == "s":
            _start(io, choices, runner)
        else:
            io.echo(f"Unknown option: {action!r}")


__all__ = [
    "DebateChoices",
    "DebateRunner",
    "MenuIO",
    "ScriptedIO",
    "initial_choices",
    "run_menu",
]
