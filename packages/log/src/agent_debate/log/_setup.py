"""structlog setup factory for ``agent_debate.log`` (TASKS.md 1.1, issue #16).

:func:`configure` wires structlog with the two sinks mandated by PRD §5.8:

* a **human-readable console renderer** (pretty, dev-facing) on stdout, and
* a **per-run JSONL file** at ``<runs_dir>/<run_id>/<run_id>.jsonl`` (machine-readable).

The factory is **idempotent** — repeat calls for the same run reuse the open
file handle and re-apply the same configuration without duplicating sinks or
raising. The runs directory is parameterised (no scattered literal): it
defaults to :data:`DEFAULT_RUNS_DIR` and the JSONL path is always
``<runs_dir>/<run_id>.jsonl``. The directory is created if missing.

This task is intentionally scoped to the configuration factory only; the event
schema, ``get_logger``/``log_event`` helpers and redaction land in later tasks
(1.2–1.5) and build on the processor chain assembled here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import structlog
from agent_debate.log._rotation import RotatingJsonlSink, load_rotation_config
from agent_debate.log.redaction import redact_event

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


class _LineSink(Protocol):
    """A minimal write-only line sink (satisfied by ``TextIO`` and the rotator)."""

    def write(self, line: str, /) -> object:
        """Write one already-newline-terminated line."""

    def flush(self) -> object:
        """Flush buffered output."""


#: Default directory (relative to the process cwd) for per-run JSONL sinks.
#: Single source of truth so the path is not hard-coded at call sites.
DEFAULT_RUNS_DIR = "runs"

#: File extension for the per-run machine-readable sink.
_JSONL_SUFFIX = ".jsonl"

#: Cache of open run sinks keyed by their resolved path, so a repeated
#: :func:`configure` for the same run reuses one rotating sink (idempotency).
_OPEN_SINKS: dict[Path, RotatingJsonlSink] = {}


def _resolve_jsonl_path(run_id: str, runs_dir: Path | str) -> Path:
    """Return the resolved ``<runs_dir>/<run_id>/<run_id>.jsonl`` path.

    Each run lives in its own subfolder (``<runs_dir>/<run_id>/``) so the JSONL
    and the companion ``.md`` are co-located. The directory is created when
    absent.
    """
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return (run_dir / run_id).with_suffix(_JSONL_SUFFIX)


def _open_sink(path: Path) -> RotatingJsonlSink:
    """Open (or reuse) the FIFO-rotating JSONL sink for ``path`` (issue #217).

    The live file is always ``path`` itself (backward compatible); older
    segments roll over to ``<stem>.N<suffix>`` and the oldest is dropped first
    once the configured file/line caps are hit. Caps come from
    ``config/logging.json`` via :func:`load_rotation_config`.
    """
    cached = _OPEN_SINKS.get(path)
    if cached is not None and not cached.closed:
        return cached
    sink = RotatingJsonlSink(path, load_rotation_config())
    _OPEN_SINKS[path] = sink
    return sink


def configure(
    run_id: str,
    *,
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
) -> FilteringBoundLogger:
    """Configure structlog and return a logger bound to ``run_id``.

    The returned logger writes to **both** sinks: a pretty console renderer on
    stdout and a JSONL file at ``<runs_dir>/<run_id>/<run_id>.jsonl``. The
    per-run subdirectory is created when absent. Calling this again for the
    same ``run_id`` is a no-op for the sinks (idempotent) and simply returns a
    freshly bound logger.

    Args:
        run_id: Identifier of the debate run; names the JSONL file.
        runs_dir: Directory holding per-run JSONL files (default ``"runs"``).

    Returns:
        A structlog logger pre-bound with ``run_id``.
    """
    jsonl_path = _resolve_jsonl_path(run_id, runs_dir)
    sink = _open_sink(jsonl_path)

    structlog.configure(
        processors=_build_processors(sink),
        cache_logger_on_first_use=False,
    )
    logger: FilteringBoundLogger = structlog.get_logger().bind(run_id=run_id)
    return logger


def _build_processors(sink: _LineSink) -> list[structlog.typing.Processor]:
    """Build the chain: redact secrets/truncate, then the dual-sink renderer.

    :func:`~agent_debate.log.redaction.redact_event` runs immediately before the
    terminal :class:`_DualSinkRenderer` so redaction/truncation applies to both
    the console and JSONL sinks (TASKS.md 1.4).
    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_event,
        _DualSinkRenderer(sink),
    ]


class _DualSinkRenderer:
    """Final processor that writes JSONL to ``sink`` and pretty to stdout.

    structlog runs a single processor chain per logger; this terminal processor
    fans the same event out to both sinks. It serialises the event dict as one
    JSON line into the per-run file and renders a human-readable line via
    structlog's :class:`~structlog.dev.ConsoleRenderer` to stdout, then drops
    the event (returns ``""``) so the default ``PrintLogger`` prints nothing
    extra.
    """

    def __init__(self, sink: _LineSink) -> None:
        self._sink = sink
        self._json = structlog.processors.JSONRenderer()
        self._console = structlog.dev.ConsoleRenderer(colors=False)

    def __call__(
        self,
        logger: object,
        method_name: str,
        event_dict: structlog.typing.EventDict,
    ) -> str:
        line = self._json(logger, method_name, dict(event_dict))
        if isinstance(line, bytes):  # JSONRenderer may emit bytes; sink is text.
            line = line.decode("utf-8")
        self._sink.write(f"{line}\n")
        self._sink.flush()
        rendered = self._console(logger, method_name, dict(event_dict))
        print(rendered)  # noqa: T201 — console sink (PRD §5.8 dev renderer)
        return ""
