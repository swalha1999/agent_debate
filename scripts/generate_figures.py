#!/usr/bin/env python
"""Render the PRD §9 charts from the saved runs (TASKS.md 14.3, issue #99).

Reads every ``runs/<run_id>.jsonl`` LOG event log (via the 14.1 aggregation and
the 14.2 analysis functions) and writes the §9 charts as PNGs — who-wins, agree
vs disagree, per-side drift/nudges, and tokens/latency per round for the largest
run. All charting lives in :mod:`agent_debate.core.research.viz`; this is the
thin CLI, mirroring ``scripts/aggregate_runs.py``.

The runs directory and the output directory are CLI flags (defaulting to the LOG
package's :data:`~agent_debate.log.DEFAULT_RUNS_DIR` and ``notebooks/figures``) —
no hard-coded magic paths. This tool makes **no external API calls**; it only
reads the already-committed run files, so the Epic-13 gatekeeper rule is N/A.
Requires the ``viz`` extra (``uv sync --group viz``) for matplotlib.

Usage (from the repo root)::

    uv run --group viz python scripts/generate_figures.py
    uv run --group viz python scripts/generate_figures.py --runs-dir runs --out notebooks/figures
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from agent_debate.core.research import (
    aggregate_runs,
    round_metrics,
    save_all_figures,
)
from agent_debate.log import DEFAULT_RUNS_DIR

# The console may echo non-Latin topic text; force UTF-8 so a legacy Windows code
# page never trips this build-time tool.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(message)s")
_LOG = logging.getLogger("generate_figures")

#: Default committed location for the generated figures (under notebooks/).
_DEFAULT_OUT = Path("notebooks") / "figures"


def _parse_args() -> argparse.Namespace:
    """Parse the runs-dir + output-dir flags (no hard-coded paths in code)."""
    parser = argparse.ArgumentParser(description="Render runs/*.jsonl into §9 chart PNGs.")
    parser.add_argument(
        "--runs-dir", default=DEFAULT_RUNS_DIR, help="Directory of <run_id>.jsonl logs."
    )
    parser.add_argument("--out", default=str(_DEFAULT_OUT), help="Output directory for PNGs.")
    return parser.parse_args()


def main() -> None:
    """Aggregate the runs and write every §9 chart to ``--out``."""
    args = _parse_args()
    summaries = aggregate_runs(args.runs_dir)
    rounds = []
    run_id = ""
    if summaries:
        largest = max(summaries, key=lambda s: s.rounds)
        run_id = largest.run_id
        lines = (Path(args.runs_dir) / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
        rounds = round_metrics(lines)
    paths = save_all_figures(summaries, args.out, rounds=rounds, run_id=run_id)
    _LOG.info("Wrote %d figure(s) to %s", len(paths), args.out)
    for path in paths:
        _LOG.info("  %s", path)


if __name__ == "__main__":
    main()
