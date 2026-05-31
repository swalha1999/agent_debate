"""Tests for the runs-dataset aggregator (issue #97, task 14.1, PRD §9).

TDD-first: these pin the 14.1 contract — read ``runs/<run_id>.jsonl`` LOG event
lines and fold them into one tidy :class:`RunSummary` per run (topic, rounds,
winner, converged, total tokens, estimated cost, per-side message + nudge counts,
latency, timeout/retry counts), then a stdlib-CSV dataset writer with a documented
column header. Synthetic in-memory JSONL fixtures (not the committed sample runs)
so the assertions never depend on those files staying fixed. Cost is priced from a
tmp :class:`PriceTable` (distinctive numbers → expected cost) so it pins to config,
never to hard-coded prices. No network, no key, no real run files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from agent_debate.core import PriceTable
from agent_debate.core.research import (
    DATASET_COLUMNS,
    RunSummary,
    aggregate_runs,
    parse_run,
    summary_to_row,
    write_dataset,
)

_PRICES = PriceTable.model_validate(
    {
        "version": "test",
        "models": {"default": {"input_per_1m": 2.0, "output_per_1m": 8.0}},
    }
)


def _event(**kwargs: object) -> str:
    """Render one LOG event dict as a JSONL line (defaults fill the schema)."""
    base: dict[str, object] = {
        "run_id": "r1",
        "round": 0,
        "agent": "controller",
        "event_type": "system",
        "payload": {},
        "tokens": None,
        "latency_ms": None,
    }
    base.update(kwargs)
    return json.dumps(base)


def _sample_lines() -> list[str]:
    """A small synthetic run: setup, 2 pro + 2 con messages, a nudge, a verdict."""
    return [
        _event(
            event_type="system",
            payload={"event": "debate_setup", "topic": "Is X good?"},
        ),
        _event(agent="pro", round=1, event_type="message", tokens=100, latency_ms=10.0),
        _event(agent="con", round=1, event_type="message", tokens=200, latency_ms=20.0),
        _event(agent="pro", round=2, event_type="message", tokens=300, latency_ms=30.0),
        _event(agent="con", round=2, event_type="message", tokens=400, latency_ms=40.0),
        _event(agent="con", round=2, event_type="nudge", payload={"side": "con"}),
        _event(agent="pro", round=2, event_type="timeout"),
        _event(agent="pro", round=2, event_type="retry"),
        _event(
            event_type="verdict",
            payload={"winner": "pro", "converged": False},
        ),
    ]


def test_parse_run_outcomes_and_topic() -> None:
    """Topic, winner and converged flag are read from setup + verdict payloads."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    assert summary.run_id == "r1"
    assert summary.topic == "Is X good?"
    assert summary.winner == "pro"
    assert summary.converged is False
    assert summary.rounds == 2


def test_parse_run_per_side_counts() -> None:
    """Per-side message and nudge counts are tallied separately."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    assert summary.pro_messages == 2
    assert summary.con_messages == 2
    assert summary.con_nudges == 1
    assert summary.pro_nudges == 0


def test_parse_run_tokens_latency_and_reliability() -> None:
    """Tokens/latency sum over messages; timeout/retry counts are captured."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    assert summary.total_tokens == 1000
    assert summary.total_latency_ms == 100.0
    assert summary.avg_latency_ms == 25.0
    assert summary.timeouts == 1
    assert summary.retries == 1


def test_parse_run_cost_priced_from_config() -> None:
    """Estimated cost prices total tokens at the config input rate (2.0/1M)."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    assert summary.est_cost_usd == 1000 / 1_000_000 * 2.0


def test_aggregate_runs_reads_jsonl_dir(tmp_path: Path) -> None:
    """``aggregate_runs`` discovers every ``*.jsonl`` and returns sorted rows."""
    (tmp_path / "b-run.jsonl").write_text("\n".join(_sample_lines()), encoding="utf-8")
    a_lines = _sample_lines()
    a_lines[-1] = _event(event_type="verdict", payload={"winner": "tie", "converged": True})
    (tmp_path / "a-run.jsonl").write_text("\n".join(a_lines), encoding="utf-8")
    summaries = aggregate_runs(tmp_path, price_table=_PRICES)
    assert [s.run_id for s in summaries] == ["a-run", "b-run"]
    assert summaries[0].winner == "tie"
    assert summaries[0].converged is True


def test_aggregate_skips_non_debate_logs(tmp_path: Path) -> None:
    """Package LOG chatter files (no setup/verdict) are excluded from the dataset."""
    (tmp_path / "debate.jsonl").write_text("\n".join(_sample_lines()), encoding="utf-8")
    chatter = json.dumps({"run_id": "api.app", "event": "started", "level": "info"})
    (tmp_path / "api.jsonl").write_text(chatter, encoding="utf-8")
    summaries = aggregate_runs(tmp_path, price_table=_PRICES)
    assert [s.run_id for s in summaries] == ["debate"]


def test_write_dataset_round_trips(tmp_path: Path) -> None:
    """The CSV has the documented header and one data row per summary."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    out = tmp_path / "data" / "runs_summary.csv"
    write_dataset([summary], out)
    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert list(rows[0].keys()) == list(DATASET_COLUMNS)
    assert rows[0]["run_id"] == "r1"
    assert rows[0]["winner"] == "pro"
    assert int(rows[0]["total_tokens"]) == 1000


def test_summary_to_row_matches_columns() -> None:
    """Every dataset column maps to a value (no missing/extra keys)."""
    summary = parse_run("r1", _sample_lines(), price_table=_PRICES)
    row = summary_to_row(summary)
    assert set(row) == set(DATASET_COLUMNS)


def test_empty_run_is_safe() -> None:
    """A run with no messages yields zeroed counts and a 0.0 average latency."""
    summary = RunSummary.empty("blank")
    assert summary.total_tokens == 0
    assert summary.avg_latency_ms == 0.0
    assert summary.winner == "n/a"
