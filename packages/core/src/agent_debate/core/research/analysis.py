"""Pure analysis functions over the runs dataset (task 14.2, PRD §9).

The 14.1 aggregation folds each ``runs/<run_id>.jsonl`` into a tidy
:class:`~agent_debate.core.research._summary.RunSummary`. This module turns those
rows (and, for round-level detail the summary does not carry, the raw JSONL
events) into the four PRD §9 analyses, as plain Python data so the
``notebooks/analysis.ipynb`` notebook stays thin:

* :func:`who_wins` — who-wins distribution (counts per winner, ties included).
* :func:`agree_vs_disagree` — converged (agree) vs not (disagree) outcome rates.
* :func:`nudges_per_side` — drift/nudge frequency per side (anti-sycophancy
  evidence: how often the controller had to correct each debater).
* :func:`round_metrics` — tokens & latency per round (parsed from the JSONL).
* :func:`tokens_latency_per_topic` — per-topic tokens & average latency.

Every function is pure and reads only the data passed in — no hard-coded paths
or values, no external API calls. The notebook supplies the runs directory via
the 14.1 :data:`~agent_debate.log.DEFAULT_RUNS_DIR` default.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable

from agent_debate.core.research._summary import RunSummary
from pydantic import BaseModel, ConfigDict

_MESSAGE = "message"
_SIDES = ("pro", "con")


def who_wins(summaries: Iterable[RunSummary]) -> dict[str, int]:
    """Return the who-wins distribution: a count per ``winner`` label.

    Ties (and the ``n/a`` no-verdict sentinel, should it appear) are kept as
    their own keys so the distribution is faithful to the dataset.

    :param summaries: The aggregated per-run rows.
    :returns: Mapping of winner label to the number of runs it won.
    """
    return dict(Counter(s.winner for s in summaries))


def agree_vs_disagree(summaries: Iterable[RunSummary]) -> dict[str, float]:
    """Return the agree-vs-disagree outcome rate from the ``converged`` flag.

    :param summaries: The aggregated per-run rows.
    :returns: ``agree``/``disagree`` counts plus the fractional ``agree_rate``
        (``0.0`` for an empty dataset, never a division error).
    """
    rows = list(summaries)
    agree = sum(1 for s in rows if s.converged)
    disagree = len(rows) - agree
    rate = agree / len(rows) if rows else 0.0
    return {"agree": agree, "disagree": disagree, "agree_rate": rate}


class NudgeStats(BaseModel):
    """Per-side drift/nudge totals plus a per-run breakdown (anti-sycophancy)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pro_total: int
    con_total: int
    per_run: dict[str, tuple[int, int]]

    @property
    def total(self) -> int:
        """Total nudges across both sides (overall controller corrections)."""
        return self.pro_total + self.con_total


def nudges_per_side(summaries: Iterable[RunSummary]) -> NudgeStats:
    """Return drift/nudge frequency per side — evidence anti-sycophancy works.

    A low/zero count means the controller rarely had to pull a captured debater
    back to its assigned side.

    :param summaries: The aggregated per-run rows.
    :returns: :class:`NudgeStats` with pro/con totals and a ``run_id`` →
        ``(pro_nudges, con_nudges)`` breakdown.
    """
    rows = list(summaries)
    per_run = {s.run_id: (s.pro_nudges, s.con_nudges) for s in rows}
    return NudgeStats(
        pro_total=sum(s.pro_nudges for s in rows),
        con_total=sum(s.con_nudges for s in rows),
        per_run=per_run,
    )


class RoundMetric(BaseModel):
    """Tokens & latency for one debate round, with a per-side token split."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    round: int
    tokens: int
    latency_ms: float
    pro_tokens: int
    con_tokens: int


def round_metrics(lines: Iterable[str]) -> list[RoundMetric]:
    """Aggregate per-round tokens & latency from one run's JSONL ``lines``.

    The 14.1 :class:`RunSummary` only carries run-level totals, so the per-round
    view is parsed straight from the LOG ``message`` events here.

    :param lines: JSONL event strings for a single run (the per-run event log).
    :returns: One :class:`RoundMetric` per round that has message events, sorted
        by round number.
    """
    tokens: Counter[int] = Counter()
    latency: dict[int, float] = {}
    per_side: dict[int, dict[str, int]] = {}
    for line in lines:
        text = line.strip()
        if not text:
            continue
        event = json.loads(text)
        if event.get("event_type") != _MESSAGE:
            continue
        _accumulate(event, tokens, latency, per_side)
    return [
        RoundMetric(
            round=rnd,
            tokens=tokens[rnd],
            latency_ms=latency.get(rnd, 0.0),
            pro_tokens=per_side.get(rnd, {}).get("pro", 0),
            con_tokens=per_side.get(rnd, {}).get("con", 0),
        )
        for rnd in sorted(tokens)
    ]


def _accumulate(
    event: dict[str, object],
    tokens: Counter[int],
    latency: dict[int, float],
    per_side: dict[int, dict[str, int]],
) -> None:
    """Fold one message event into the per-round token/latency tallies."""
    rnd = event.get("round")
    if not isinstance(rnd, int):
        return
    tok = event.get("tokens")
    tok_int = tok if isinstance(tok, int) else 0
    tokens[rnd] += tok_int
    lat = event.get("latency_ms")
    if isinstance(lat, (int, float)):
        latency[rnd] = latency.get(rnd, 0.0) + float(lat)
    side = str(event.get("agent"))
    if side in _SIDES:
        per_side.setdefault(rnd, {})[side] = per_side.get(rnd, {}).get(side, 0) + tok_int


class TopicMetric(BaseModel):
    """Tokens & latency rolled up for one topic/run (one row per run)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    topic: str
    rounds: int
    total_tokens: int
    avg_latency_ms: float


def tokens_latency_per_topic(summaries: Iterable[RunSummary]) -> list[TopicMetric]:
    """Return per-topic tokens & average latency from the summary rows.

    :param summaries: The aggregated per-run rows.
    :returns: One :class:`TopicMetric` per run, in the order supplied.
    """
    return [
        TopicMetric(
            run_id=s.run_id,
            topic=s.topic,
            rounds=s.rounds,
            total_tokens=s.total_tokens,
            avg_latency_ms=s.avg_latency_ms,
        )
        for s in summaries
    ]


__all__ = [
    "NudgeStats",
    "RoundMetric",
    "TopicMetric",
    "agree_vs_disagree",
    "nudges_per_side",
    "round_metrics",
    "tokens_latency_per_topic",
    "who_wins",
]
