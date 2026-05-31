"""``--json`` output + failure semantics for ``run`` (task 9.3, issue #66).

PRD §6: ``--json`` emits the :class:`~agent_debate.core.engine.result.DebateResult`
as machine-readable JSON (a single blob via Pydantic's ``model_dump_json``) for
piping/parsing, and the command exits NON-ZERO on failure. Split out of
:mod:`agent_debate.cli.app` (PRD §3.2: split, don't compress) so the command stays
thin and under the 150-line cap.

Failure semantics (shared by BOTH the human and ``--json`` paths so behaviour is
consistent): a debate that cannot produce a valid result — a missing API key
(:class:`~agent_debate.core.MissingApiKeyError`), an invalid topic
(:class:`~agent_debate.core.InvalidInputError`), a turn exhausting its retry budget
(:class:`~agent_debate.core.engine._call.TurnFailedError`), or any other engine
error — is reported to ``stderr`` (never polluting the JSON on ``stdout``) and the
process exits with :data:`EXIT_FAILURE` (a NAMED constant, no magic number).
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, NoReturn

import typer
from agent_debate.core import InvalidInputError, MissingApiKeyError
from agent_debate.core.engine._call import TurnFailedError

if TYPE_CHECKING:
    from agent_debate.core.engine.result import DebateResult
    from structlog.typing import FilteringBoundLogger

#: Process exit code on a debate failure (non-zero; no magic numbers).
EXIT_FAILURE = 1

#: Exceptions that mean "the debate could not produce a valid result". Surfaced
#: as a clean error + non-zero exit rather than an opaque traceback.
_DEBATE_FAILURES: tuple[type[Exception], ...] = (
    MissingApiKeyError,
    InvalidInputError,
    TurnFailedError,
)


@contextlib.contextmanager
def clean_stdout() -> Iterator[None]:
    """Divert the LOG console sink off stdout for the duration of the block.

    The LOG package mirrors every event to a pretty console sink on ``stdout``
    (PRD §5.8). In ``--json`` mode that would pollute the single JSON blob, so we
    temporarily point ``sys.stdout`` at ``sys.stderr`` while the engine runs and
    logs; the JSON itself is written afterwards to the real stdout via
    :func:`emit_json`. ``stdout`` is always restored, even on error.
    """
    original = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original


def emit_json(result: DebateResult) -> None:
    """Print ``result`` as a single machine-readable JSON blob on stdout.

    Uses Pydantic's :meth:`DebateResult.model_dump_json` so the output is the
    canonical serialisation (transcript, nudges, closing discussion, verdict,
    totals). ONLY the JSON is written to stdout — no Rich decoration — so the
    output stays pipeable/parseable.
    """
    typer.echo(result.model_dump_json())


def run_or_fail[R](
    produce: Callable[[], R],
    *,
    log: FilteringBoundLogger,
) -> R:
    """Call ``produce`` and return its result, or fail cleanly + non-zero.

    On a known debate failure (missing key / invalid input / a turn exhausting
    its retries) or any other engine error, log the failure, print a concise
    message to ``stderr`` (keeping ``stdout`` clean for JSON), and raise
    :class:`typer.Exit` with :data:`EXIT_FAILURE` so the process exits non-zero.
    """
    try:
        return produce()
    except _DEBATE_FAILURES as exc:
        _fail(log, exc)
    except Exception as exc:  # noqa: BLE001 — any engine error must exit non-zero
        _fail(log, exc)


def _fail(log: FilteringBoundLogger, exc: Exception) -> NoReturn:
    """Log + report ``exc`` on stderr and exit non-zero (never returns)."""
    log.error("cli_run_failed", error=str(exc), error_type=type(exc).__name__)
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=EXIT_FAILURE)


__all__ = ["EXIT_FAILURE", "clean_stdout", "emit_json", "run_or_fail"]
