#!/usr/bin/env python
"""Embed a per-debate round-token chart into each run's transcript (PRD §9).

For every committed debate run under ``runs/`` this renders a tokens-per-round
chart (grouped pro vs con bars) to ``runs/<run_id>/<run_id>-round-tokens.png``
and splices a ``## Round-by-round token usage`` section into the matching
``runs/<run_id>/<run_id>.md`` so each transcript is self-contained. The image
reference is a bare filename (same-folder relative path) since the PNG sits
beside the ``.md``.

Run discovery reuses the 14.1 aggregation
(:func:`~agent_debate.core.research.aggregate_runs`), so only real debate runs
are processed — ``dataset/`` and side-channel LOG dirs are skipped. The runs
directory is a CLI flag defaulting to the LOG package's
:data:`~agent_debate.log.DEFAULT_RUNS_DIR`; no hard-coded paths. The Markdown
edit is idempotent (re-running replaces the section, never duplicates it). This
tool makes **no external API calls** — it only reads committed run files and
renders charts offline. Requires the ``viz`` extra (``uv sync --group viz``).

Usage (from the repo root)::

    uv run --group viz python scripts/embed_round_charts.py
    uv run --group viz python scripts/embed_round_charts.py --runs-dir runs
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from agent_debate.core.research import (
    aggregate_runs,
    embed_round_chart_section,
    round_metrics,
    save_run_round_tokens_chart,
)
from agent_debate.log import DEFAULT_RUNS_DIR

# The console may echo non-Latin topic text; force UTF-8 so a legacy Windows code
# page (e.g. cp1255) never trips this build-time tool.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(message)s")
_LOG = logging.getLogger("embed_round_charts")


def _parse_args() -> argparse.Namespace:
    """Parse the runs-dir flag (no hard-coded paths in code)."""
    parser = argparse.ArgumentParser(description="Embed per-run round-token charts into each .md.")
    parser.add_argument(
        "--runs-dir", default=str(DEFAULT_RUNS_DIR), help="Directory of per-run subfolders."
    )
    return parser.parse_args()


def _embed_one(runs_dir: Path, run_id: str) -> Path:
    """Render the chart and embed it into ``run_id``'s transcript; return the PNG."""
    run_dir = runs_dir / run_id
    lines = (run_dir / f"{run_id}.jsonl").read_text(encoding="utf-8").splitlines()
    rounds = round_metrics(lines)
    png = run_dir / f"{run_id}-round-tokens.png"
    save_run_round_tokens_chart(rounds, png, run_id)
    md_path = run_dir / f"{run_id}.md"
    updated = embed_round_chart_section(md_path.read_text(encoding="utf-8"), png.name)
    md_path.write_text(updated, encoding="utf-8")
    return png


def main() -> None:
    """Render and embed a round-token chart for every discovered debate run."""
    args = _parse_args()
    runs_dir = Path(args.runs_dir)
    summaries = aggregate_runs(runs_dir)
    for summary in summaries:
        png = _embed_one(runs_dir, summary.run_id)
        _LOG.info("Embedded %s (%d rounds) -> %s", summary.run_id, summary.rounds, png)
    _LOG.info("Processed %d run(s) under %s", len(summaries), runs_dir)


if __name__ == "__main__":
    main()
