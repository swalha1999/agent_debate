"""Public SDK entrypoint — :class:`DebateEngine` (issue #53, task 6.8, §6).

PRD §6 (SDK surface): ``DebateEngine(config).run(topic)`` returns a structured
:class:`~agent_debate.core.engine.result.DebateResult` (transcript, nudges,
verdict) and "streams events for live consumers". This module is THE library
facade the other surfaces (CLI/API/UI, Epics 9-11) drive — a single ergonomic
class that ties the engine's :func:`~agent_debate.core.engine.setup.setup_debate`
+ :func:`~agent_debate.core.engine.loop.run_debate_loop` +
:func:`~agent_debate.core.engine.stream.stream_debate` seams together.

The canonical import path is ``from agent_debate.core import DebateEngine`` (the
SDK is the ``agent_debate.core`` namespace package — there is no top-level
``agent_debate.__init__`` to hang a shim on, so this is THE documented surface,
matching the PRD's ``from agent_debate import DebateEngine`` intent).

Config-driven, no hard-coding: when ``config`` is ``None`` it is built from
:class:`~agent_debate.core.settings.Settings` via
:meth:`DebateConfig.from_settings`; the API gatekeeper (Epic 13) is injected or
left to the loop's config-driven default so EVERY model call stays rate-limited.

Streaming contract. :meth:`run` is the blocking call that returns the final
:class:`DebateResult`. :meth:`stream` is the streaming variant: it yields each
ordered, typed :class:`~agent_debate.log.LogEvent` live as it happens, and the
FINAL item it yields is the completed :class:`DebateResult` — so a consumer can
both render live and capture the full result from one iterator.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

from agent_debate.core.engine.gatekeeper_proto import Gatekeeper
from agent_debate.core.engine.loop import run_debate_loop
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.engine.setup import SetupModels, setup_debate
from agent_debate.core.engine.stream import stream_debate
from agent_debate.core.settings import Settings, get_settings
from agent_debate.log import DEFAULT_RUNS_DIR, LogEvent


class DebateEngine:
    """The public SDK facade: ``DebateEngine(config).run(topic)`` (PRD §6).

    Holds the run :class:`DebateConfig` (config-driven, from
    :class:`~agent_debate.core.settings.Settings` when omitted), the settings,
    the optional injected API gatekeeper and per-agent ``models`` map, and the
    run-log directory. :meth:`run` executes a full debate and returns the
    :class:`DebateResult`; :meth:`stream` yields events live then the result.
    """

    def __init__(
        self,
        config: DebateConfig | None = None,
        *,
        settings: Settings | None = None,
        gatekeeper: Gatekeeper | None = None,
        models: SetupModels | None = None,
        runs_dir: Path | str = DEFAULT_RUNS_DIR,
    ) -> None:
        """Build the engine; ``config`` defaults to ``DebateConfig.from_settings``.

        Args:
            config: The run config; when ``None`` it is derived from ``settings``
                (or the process settings) so defaults track configuration.
            settings: Configuration to read; defaults to the process settings.
            gatekeeper: The API gatekeeper to route model calls through. When
                ``None`` the loop builds its own config-driven default bound to
                the run id, so calls stay rate-limited (Epic 13) — never bypassed.
            models: Optional per-agent models (tests inject ``TestModel`` to run
                fully offline); absent injection the configured models are used.
            runs_dir: Directory holding the per-run JSONL event log.
        """
        self.settings = settings or get_settings()
        self.config = config or DebateConfig.from_settings(self.settings)
        self._gatekeeper = gatekeeper
        self._models = models
        self._runs_dir = runs_dir

    def run(self, topic: str, *, run_id: str | None = None) -> DebateResult:
        """Run a full debate on ``topic`` and return the :class:`DebateResult`.

        Validates the topic (via :func:`setup_debate`, which calls the 7.2
        security validator), prepares the agents/contexts, then runs the loop to
        completion. A ``run_id`` is minted (uuid4) when not supplied.

        Args:
            topic: The user-supplied debate topic (validated before use).
            run_id: Explicit run id; a uuid4 is generated when ``None``.

        Returns:
            The completed :class:`DebateResult` (transcript, nudges, closing
            discussion, totals).
        """
        resolved_id = run_id or _new_run_id()
        setup = self._setup(topic, resolved_id, log_setup=True)
        return run_debate_loop(
            setup,
            self.config,
            gatekeeper=self._gatekeeper,
            run_id=resolved_id,
            runs_dir=self._runs_dir,
        )

    def stream(self, topic: str, *, run_id: str | None = None) -> Iterator[LogEvent | DebateResult]:
        """Stream a debate: yield ordered events live, then the final result.

        The streaming variant of :meth:`run`. Each :class:`~agent_debate.log.
        LogEvent` is yielded as it happens (so live consumers render round by
        round); the FINAL item yielded is the completed :class:`DebateResult`.

        Args:
            topic: The user-supplied debate topic (validated before use).
            run_id: Explicit run id; a uuid4 is generated when ``None``.

        Yields:
            Each :class:`~agent_debate.log.LogEvent` in order, then the final
            :class:`DebateResult`.
        """
        resolved_id = run_id or _new_run_id()
        setup = self._setup(topic, resolved_id, log_setup=False)
        yield from stream_debate(
            setup,
            self.config,
            gatekeeper=self._gatekeeper,
            run_id=resolved_id,
            runs_dir=self._runs_dir,
        )

    def _setup(self, topic: str, run_id: str, *, log_setup: bool):  # type: ignore[no-untyped-def]
        """Validate + prepare the run state shared by :meth:`run` / :meth:`stream`.

        ``log_setup`` controls whether the one ``system`` setup event is emitted:
        :meth:`run` logs it for observability, while :meth:`stream` skips it so the
        yielded event sequence stays identical to the JSONL log written by the loop
        (the setup event precedes the streamed worker and would otherwise not be
        pushed through the live sink).
        """
        return setup_debate(
            topic,
            self.config,
            settings=self.settings,
            models=self._models,
            run_id=run_id if log_setup else None,
            runs_dir=self._runs_dir,
        )


def _new_run_id() -> str:
    """Mint a fresh, collision-resistant run id (uuid4 hex)."""
    return uuid.uuid4().hex


__all__ = ["DebateEngine"]
