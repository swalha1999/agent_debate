"""Render a completed :class:`DebateResult` as a readable ``runs/<run_id>/<run_id>.md`` (12.5).

PRD §10/§11 + TASKS.md 12.5: the teacher reviews a human-readable markdown document
per sample run — the topic, the full transcript (grouped by round), the closing
discussion, the controller's anti-sycophancy nudges, the final verdict, and the
cost-breakdown table. The companion machine log is ``runs/<run_id>.jsonl`` (written
by the LOG package as the debate runs); this module renders the readable view from
the same completed :class:`~agent_debate.core.engine.result.DebateResult`, which
already carries the priced ``cost_breakdown``.

The cost table reuses :func:`~agent_debate.core.pricing.format_cost_table` verbatim
(via :mod:`agent_debate.core.export._sections`) — no pricing or table markdown is
duplicated (§4, no duplication). :func:`render_run_markdown` is a pure function (no
I/O); :func:`write_run_markdown` is the thin file sink the run generator calls.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.engine.result import DebateResult
from agent_debate.core.export._sections import (
    closing_section,
    cost_section,
    nudges_section,
    transcript_section,
    verdict_section,
)
from agent_debate.log import DEFAULT_RUNS_DIR

#: File extension of the readable per-run document (the JSONL log is the companion).
_MARKDOWN_SUFFIX = ".md"


def render_run_markdown(result: DebateResult, *, run_id: str) -> str:
    """Render ``result`` as the readable run markdown document for ``run_id``.

    Assembles the title (topic + run id), the round-grouped transcript, the closing
    discussion, the controller nudges, the verdict and the cost/token section into a
    single markdown string. Pure — no file or network I/O. Missing pieces (no
    verdict, no priced cost breakdown) degrade gracefully to a short note rather than
    raising, so an aborted/partial run still renders.

    Args:
        result: The completed (ideally priced) debate result to render.
        run_id: The run id this document belongs to (shown in the header + used by
            :func:`write_run_markdown` for the file name).

    Returns:
        The full markdown document as one string (newline-terminated sections).
    """
    lines = [
        f"# Debate run `{run_id}`",
        "",
        f"**Topic:** {result.topic}",
        "",
        *transcript_section(result.transcript),
        *closing_section(result.closing_discussion),
        *nudges_section(result.nudges),
        *verdict_section(result.verdict),
        *cost_section(result),
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_run_markdown(
    result: DebateResult, *, run_id: str, runs_dir: Path | str = DEFAULT_RUNS_DIR
) -> Path:
    """Render ``result`` and write it to ``<runs_dir>/<run_id>/<run_id>.md`` (UTF-8).

    Each run lives in its own subfolder so the readable ``.md`` is co-located
    with the LOG package's ``<run_id>.jsonl`` machine log. The per-run
    subdirectory is created when absent.

    Args:
        result: The completed debate result to render.
        run_id: The run id (file stem, subfolder name, and document header).
        runs_dir: Parent runs directory (default the LOG runs dir).

    Returns:
        The path of the written ``<run_id>.md`` file.
    """
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{run_id}{_MARKDOWN_SUFFIX}"
    path.write_text(render_run_markdown(result, run_id=run_id), encoding="utf-8")
    return path


__all__ = ["render_run_markdown", "write_run_markdown"]
