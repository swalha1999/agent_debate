"""Discover and fold every ``runs/*.jsonl`` into the dataset (task 14.1, PRD §9).

Walks a runs directory (default :data:`agent_debate.log.DEFAULT_RUNS_DIR` — no
hard-coded path), parses each ``<run_id>.jsonl`` event log into a
:class:`~agent_debate.core.research._summary.RunSummary` via
:func:`~agent_debate.core.research._parse.parse_run`, and returns the rows sorted
by ``run_id`` for a stable, tidy dataset. Progress is logged through the LOG
package. No external API calls — this only reads committed run files.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.pricing import PriceTable
from agent_debate.core.research._parse import is_debate_run, parse_run
from agent_debate.core.research._summary import RunSummary
from agent_debate.log import DEFAULT_RUNS_DIR, get_logger

_LOG = get_logger("research.aggregate")

#: Glob matching the per-run JSONL event logs the LOG package writes.
RUN_GLOB = "*.jsonl"


def aggregate_runs(
    runs_dir: Path | str = DEFAULT_RUNS_DIR,
    *,
    price_table: PriceTable | None = None,
) -> list[RunSummary]:
    """Aggregate every ``*.jsonl`` under ``runs_dir`` into summary rows.

    :param runs_dir: Directory holding the per-run JSONL logs (defaults to the
        repo runs dir). Each file's stem becomes the row's ``run_id``.
    :param price_table: Price table for the cost estimate; loaded from config
        when ``None``.
    :returns: One :class:`RunSummary` per *debate* file, sorted by ``run_id``.
        Non-debate LOG chatter files in the directory are skipped.
    """
    directory = Path(runs_dir)
    summaries: list[RunSummary] = []
    for path in sorted(directory.glob(RUN_GLOB)):
        lines = path.read_text(encoding="utf-8").splitlines()
        if not is_debate_run(lines):
            continue
        summaries.append(parse_run(path.stem, lines, price_table=price_table))
    _LOG.info("runs_aggregated", count=len(summaries), runs_dir=str(directory))
    return summaries


__all__ = ["RUN_GLOB", "aggregate_runs"]
