"""Tests for the research analysis functions (issue #98, task 14.2, PRD §9).

TDD-first: pin the 14.2 contract — pure analysis functions over the 14.1
:class:`RunSummary` rows plus round-level parsing of the per-run JSONL events.
The four §9 analyses are covered: who-wins distribution, agree-vs-disagree rate,
drift/nudge frequency per side (anti-sycophancy evidence) and tokens/latency per
round (and per topic). Synthetic in-memory fixtures only — never the committed
sample runs — so the assertions never depend on those files staying fixed. No
network, no key, no real run files.
"""

from __future__ import annotations

import json

from agent_debate.core.research import (
    RunSummary,
    agree_vs_disagree,
    nudges_per_side,
    round_metrics,
    tokens_latency_per_topic,
    who_wins,
)


def _summary(run_id: str, **kwargs: object) -> RunSummary:
    """Build a RunSummary with sensible defaults for the fields under test."""
    return RunSummary(run_id=run_id, **kwargs)  # type: ignore[arg-type]


def _rows() -> list[RunSummary]:
    """Four synthetic rows mirroring the real dataset's winner spread."""
    return [
        _summary("a", winner="pro", converged=False, pro_nudges=1, con_nudges=0),
        _summary("b", winner="con", converged=True, pro_nudges=0, con_nudges=2),
        _summary("c", winner="tie", converged=False, pro_nudges=0, con_nudges=0),
        _summary("d", winner="pro", converged=True, pro_nudges=3, con_nudges=1),
    ]


def test_who_wins_counts_each_outcome() -> None:
    """who_wins tallies one count per winner label, ties included."""
    dist = who_wins(_rows())
    assert dist == {"pro": 2, "con": 1, "tie": 1}


def test_who_wins_empty_is_empty() -> None:
    """No rows yields an empty distribution (no crash)."""
    assert who_wins([]) == {}


def test_agree_vs_disagree_counts_converged_flag() -> None:
    """agree_vs_disagree counts converged True (agree) vs False (disagree)."""
    rates = agree_vs_disagree(_rows())
    assert rates["agree"] == 2
    assert rates["disagree"] == 2
    assert rates["agree_rate"] == 0.5


def test_agree_vs_disagree_empty_rate_is_zero() -> None:
    """An empty dataset reports a 0.0 agree rate instead of dividing by zero."""
    rates = agree_vs_disagree([])
    assert rates["agree"] == 0
    assert rates["disagree"] == 0
    assert rates["agree_rate"] == 0.0


def test_nudges_per_side_totals_and_per_run() -> None:
    """nudges_per_side sums pro/con nudges and keeps a per-run breakdown."""
    result = nudges_per_side(_rows())
    assert result.pro_total == 4
    assert result.con_total == 3
    assert result.per_run["d"] == (3, 1)
    assert result.total == 7


def test_nudges_per_side_zero_is_anti_sycophancy_evidence() -> None:
    """All-zero nudges (the real runs) report cleanly as zero totals."""
    rows = [_summary("x", pro_nudges=0, con_nudges=0)]
    result = nudges_per_side(rows)
    assert result.pro_total == 0
    assert result.con_total == 0
    assert result.total == 0


def _round_lines() -> list[str]:
    """Synthetic JSONL: 2 rounds, each a pro + con message with tokens/latency."""

    def line(**kw: object) -> str:
        base: dict[str, object] = {
            "run_id": "r",
            "round": 0,
            "agent": "controller",
            "event_type": "system",
            "payload": {},
            "tokens": None,
            "latency_ms": None,
        }
        base.update(kw)
        return json.dumps(base)

    return [
        line(agent="pro", round=1, event_type="message", tokens=100, latency_ms=10.0),
        line(agent="con", round=1, event_type="message", tokens=200, latency_ms=20.0),
        line(agent="pro", round=2, event_type="message", tokens=300, latency_ms=30.0),
        line(agent="con", round=2, event_type="message", tokens=400, latency_ms=40.0),
        line(agent="controller", round=2, event_type="verdict", payload={"winner": "pro"}),
    ]


def test_round_metrics_aggregates_tokens_latency_per_round() -> None:
    """round_metrics groups message tokens/latency by round across both sides."""
    rounds = round_metrics(_round_lines())
    assert [r.round for r in rounds] == [1, 2]
    assert rounds[0].tokens == 300
    assert rounds[0].latency_ms == 30.0
    assert rounds[1].tokens == 700
    assert rounds[1].latency_ms == 70.0


def test_round_metrics_splits_per_side() -> None:
    """Each round carries its per-side pro/con token split."""
    rounds = round_metrics(_round_lines())
    assert rounds[0].pro_tokens == 100
    assert rounds[0].con_tokens == 200
    assert rounds[1].pro_tokens == 300
    assert rounds[1].con_tokens == 400


def test_round_metrics_ignores_non_message_events() -> None:
    """Non-message events (verdict/system) do not create round rows."""
    rounds = round_metrics(_round_lines())
    assert len(rounds) == 2


def test_tokens_latency_per_topic_uses_summary_rows() -> None:
    """Per-topic view exposes each run's total tokens and average latency."""
    rows = [
        _summary("a", topic="T1", total_tokens=1000, avg_latency_ms=12.5, rounds=5),
        _summary("b", topic="T2", total_tokens=2000, avg_latency_ms=25.0, rounds=10),
    ]
    table = tokens_latency_per_topic(rows)
    assert table[0].topic == "T1"
    assert table[0].total_tokens == 1000
    assert table[0].avg_latency_ms == 12.5
    assert table[1].rounds == 10
