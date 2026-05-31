"""Injectable streaming debate runner — the SSE seam (task 10.3, issue #70).

Like :data:`~agent_debate.api.debate_runner.DebateRunner` (10.2), but for the
live ``GET /debates/{id}/stream`` path: the runner must PUBLISH each ordered,
typed :class:`~agent_debate.log.LogEvent` into the run's buffer as it happens and
still return the final :class:`~agent_debate.core.DebateResult`. So the seam is a
callable ``(topic, overrides, publish, run_id) -> DebateResult`` where ``publish``
is the per-run :meth:`~agent_debate.api.event_buffer.EventBuffer.publish`.

Production uses :func:`default_stream_runner`, which drives
:meth:`DebateEngine.stream` (every model call still routes through the Epic-13
gatekeeper inside the engine) and forwards each yielded event to ``publish``,
keeping the final :class:`DebateResult` (the last item the stream yields). Tests
inject a stub via :func:`set_stream_runner` that publishes canned events with no
network and no API key.
"""

from __future__ import annotations

from typing import Protocol

from agent_debate.api.debate_runner import RUNNER_ATTR, DebateRunner
from agent_debate.core import (
    DebateConfig,
    DebateEngine,
    DebateResult,
    get_settings,
)
from agent_debate.log import LogEvent
from fastapi import FastAPI

#: ``app.state`` attribute holding the active streaming runner (single source).
STREAM_RUNNER_ATTR = "debate_stream_runner"


class Publish(Protocol):
    """Callback that appends one live event to the run's buffer."""

    def __call__(self, event: LogEvent) -> None:
        """Publish ``event`` to the per-run buffer the SSE endpoint drains."""
        ...


class DebateStreamRunner(Protocol):
    """A callable that runs a debate, publishing each event live as it happens."""

    def __call__(
        self,
        topic: str,
        overrides: dict[str, object],
        publish: Publish,
        run_id: str,
    ) -> DebateResult:
        """Run ``topic`` (with ``overrides``), publishing events, return result."""
        ...


def default_stream_runner(
    topic: str, overrides: dict[str, object], publish: Publish, run_id: str
) -> DebateResult:
    """Drive :meth:`DebateEngine.stream`, forwarding each event to ``publish``.

    Applies ``overrides`` to the process settings (config-driven, no inline
    literals), then streams the debate: every yielded :class:`LogEvent` is
    published live; the final :class:`DebateResult` the stream yields is returned.
    """
    settings = get_settings()
    if overrides:
        settings = settings.model_copy(update=overrides)
    engine = DebateEngine(DebateConfig.from_settings(settings), settings=settings)
    result: DebateResult | None = None
    for item in engine.stream(topic, run_id=run_id):
        if isinstance(item, LogEvent):
            publish(item)
        else:
            result = item
    if result is None:  # pragma: no cover — stream always yields a final result.
        result = DebateResult(topic=topic)
    return result


def set_stream_runner(app: FastAPI, runner: DebateStreamRunner) -> None:
    """Install ``runner`` on ``app.state`` (tests substitute a stub here)."""
    setattr(app.state, STREAM_RUNNER_ATTR, runner)


def _adapt(runner: DebateRunner) -> DebateStreamRunner:
    """Wrap a non-streaming :class:`DebateRunner` as a streaming one (no events)."""

    def _wrapped(
        topic: str, overrides: dict[str, object], publish: Publish, run_id: str
    ) -> DebateResult:
        return runner(topic, overrides)

    return _wrapped


def get_stream_runner(app: FastAPI) -> DebateStreamRunner:
    """Return the streaming runner on ``app.state``.

    Resolution order (single source of truth): an explicit streaming runner
    (installed via :func:`set_stream_runner`) wins; else a non-streaming runner
    installed via :func:`~agent_debate.api.debate_runner.set_debate_runner` is
    adapted (backward compatible with 10.2); else :func:`default_stream_runner`.
    """
    streaming = getattr(app.state, STREAM_RUNNER_ATTR, None)
    if streaming is not None:
        return streaming  # type: ignore[no-any-return]
    plain = getattr(app.state, RUNNER_ATTR, None)
    if plain is not None:
        return _adapt(plain)
    return default_stream_runner


__all__ = [
    "DebateStreamRunner",
    "Publish",
    "STREAM_RUNNER_ATTR",
    "default_stream_runner",
    "get_stream_runner",
    "set_stream_runner",
]
