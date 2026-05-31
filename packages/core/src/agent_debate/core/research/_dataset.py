"""Tidy CSV serialisation for the runs dataset (task 14.1, PRD §9).

Turns :class:`~agent_debate.core.research._summary.RunSummary` rows into a
one-row-per-run CSV with a documented, stable column order (:data:`DATASET_COLUMNS`).
Stdlib ``csv`` only — no heavy data-frame dependency is added just for this. The
column list is the single source of truth: both the header and each row are built
from it, so they can never drift apart.
"""

from __future__ import annotations

import csv
from pathlib import Path

from agent_debate.core.research._summary import RunSummary

#: The dataset columns, in order. One tidy row per run (PRD §9): identity + topic,
#: outcomes, per-side message + nudge counts, tokens/cost, latency, reliability.
DATASET_COLUMNS: tuple[str, ...] = (
    "run_id",
    "topic",
    "rounds",
    "winner",
    "converged",
    "total_tokens",
    "est_cost_usd",
    "pro_messages",
    "con_messages",
    "pro_nudges",
    "con_nudges",
    "total_latency_ms",
    "avg_latency_ms",
    "timeouts",
    "retries",
)


#: Float columns rounded to keep the committed CSV clean and deterministic
#: (free of binary float noise like ``159203.9999999997``).
_FLOAT_PLACES = {
    "est_cost_usd": 6,
    "total_latency_ms": 3,
    "avg_latency_ms": 3,
}


def summary_to_row(summary: RunSummary) -> dict[str, object]:
    """Project a :class:`RunSummary` onto the :data:`DATASET_COLUMNS` mapping.

    Float columns are rounded (see :data:`_FLOAT_PLACES`) so the serialised CSV is
    stable and readable; integer/text columns are written verbatim.
    """
    row: dict[str, object] = {}
    for column in DATASET_COLUMNS:
        value = getattr(summary, column)
        places = _FLOAT_PLACES.get(column)
        row[column] = round(value, places) if places is not None else value
    return row


def write_dataset(summaries: list[RunSummary], path: Path | str) -> Path:
    """Write ``summaries`` to a tidy CSV at ``path`` (parent dirs created).

    :param summaries: The per-run rows to serialise (written in iteration order).
    :param path: Destination CSV file; missing parent directories are created.
    :returns: The resolved :class:`~pathlib.Path` written.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DATASET_COLUMNS))
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary_to_row(summary))
    return out


__all__ = ["DATASET_COLUMNS", "summary_to_row", "write_dataset"]
