#!/usr/bin/env python
"""Aggregate saved debate runs into a tidy dataset (TASKS.md 14.1, issue #97).

Reads every ``runs/<run_id>.jsonl`` LOG event log and folds it into a one-row-per-run
CSV (outcomes, per-side drift/nudge counts, tokens, latency) for the PRD §9 results
analysis. All logic lives in :mod:`agent_debate.core.research`; this is the thin CLI.

The runs directory and the output path are CLI flags (defaulting to the LOG package's
:data:`~agent_debate.log.DEFAULT_RUNS_DIR` and ``runs/dataset/runs_summary.csv``) — no
hard-coded magic paths. This tool makes **no external API calls**; it only reads the
already-committed run files, so the Epic-13 gatekeeper rule does not apply here.

Usage (from the repo root)::

    uv run python scripts/aggregate_runs.py
    uv run python scripts/aggregate_runs.py --runs-dir runs --out runs/dataset/runs_summary.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from agent_debate.core.research import aggregate_runs, write_dataset
from agent_debate.log import DEFAULT_RUNS_DIR

# The console may echo non-Latin topic text; force UTF-8 so a legacy Windows code
# page never trips this build-time tool (the CSV is written UTF-8 already).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(message)s")
_LOG = logging.getLogger("aggregate_runs")

#: Default committed location for the generated dataset (under the runs dir).
_DEFAULT_OUT = Path(DEFAULT_RUNS_DIR) / "dataset" / "runs_summary.csv"


def _parse_args() -> argparse.Namespace:
    """Parse the runs-dir + output-path flags (no hard-coded paths in code)."""
    parser = argparse.ArgumentParser(description="Aggregate runs/*.jsonl into a CSV dataset.")
    parser.add_argument(
        "--runs-dir", default=DEFAULT_RUNS_DIR, help="Directory of <run_id>.jsonl logs."
    )
    parser.add_argument("--out", default=str(_DEFAULT_OUT), help="Output CSV path.")
    return parser.parse_args()


def main() -> None:
    """Aggregate every run under ``--runs-dir`` and write the dataset to ``--out``."""
    args = _parse_args()
    summaries = aggregate_runs(args.runs_dir)
    out = write_dataset(summaries, args.out)
    _LOG.info("Wrote %d run(s) to %s", len(summaries), out)
    for summary in summaries:
        _LOG.info(
            "  %s: winner=%s tokens=%d cost=$%.6f nudges(pro/con)=%d/%d",
            summary.run_id,
            summary.winner,
            summary.total_tokens,
            summary.est_cost_usd,
            summary.pro_nudges,
            summary.con_nudges,
        )


if __name__ == "__main__":
    main()
