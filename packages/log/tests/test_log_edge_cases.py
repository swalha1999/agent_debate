"""Edge-case / boundary tests for ``agent_debate.log`` (TASKS.md 1.5, issue #20).

These close coverage *gaps* the 1.1–1.4 suites leave open — they target real
behaviours that were not previously asserted, not duplicates:

* multiple events **appended** to one ``<run_id>.jsonl`` (order + count),
* the **exactly-at-length** truncation boundary (``len == MAX_VALUE_LEN`` must
  pass through untouched; the unit suite only covers ``>`` and small),
* an **empty payload** surviving the public-API write path,
* a bound ``round`` propagating then being **cleared** within one disk flow,
* idempotent ``get_logger`` keeping a **single** sink under repeated calls
  interleaved with writes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.log import (
    MAX_VALUE_LEN,
    TRUNCATED_SUFFIX,
    bind_round,
    clear_context,
    get_logger,
    log_event,
)
from agent_debate.log.redaction import redact_value
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _reset_context() -> None:
    """Start each test with no bound contextvars (no cross-test leakage)."""
    clear_context()


def _read_lines(path: Path) -> list[dict[str, object]]:
    """Parse every non-blank JSONL line in ``path`` into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_multiple_events_append_to_same_jsonl(tmp_path: Path) -> None:
    """Successive ``log_event`` calls append (not overwrite) in emission order."""
    runs_dir = tmp_path / "runs"
    for i in range(3):
        log_event(
            run_id="multi",
            round=i,
            agent="pro",
            event_type="message",
            payload={"i": i},
            runs_dir=runs_dir,
        )

    records = _read_lines(runs_dir / "multi" / "multi.jsonl")
    assert [r["round"] for r in records] == [0, 1, 2]
    assert [r["payload"]["i"] for r in records] == [0, 1, 2]  # type: ignore[index]


def test_truncation_boundary_exact_length_passes_through() -> None:
    """A string of exactly ``MAX_VALUE_LEN`` is left intact (boundary off-by-one)."""
    exact = "a" * MAX_VALUE_LEN
    out = redact_value(exact)
    assert out == exact
    assert not out.endswith(TRUNCATED_SUFFIX)

    over = "a" * (MAX_VALUE_LEN + 1)
    out_over = redact_value(over)
    assert out_over.endswith(TRUNCATED_SUFFIX)
    assert len(out_over) == MAX_VALUE_LEN + len(TRUNCATED_SUFFIX)


def test_empty_payload_round_trips_through_public_api(tmp_path: Path) -> None:
    """An omitted payload writes an empty dict that survives to the JSONL sink."""
    runs_dir = tmp_path / "runs"
    event = log_event(
        run_id="empty",
        round=1,
        agent="con",
        event_type="system",
        runs_dir=runs_dir,
    )
    assert event.payload == {}

    record = _read_lines(runs_dir / "empty" / "empty.jsonl")[0]
    assert record["payload"] == {}


def test_bound_round_then_cleared_in_one_disk_flow(tmp_path: Path) -> None:
    """A bound round propagates; after ``clear_context`` it no longer applies."""
    runs_dir = tmp_path / "runs"
    get_logger("ctx", runs_dir=runs_dir)

    bind_round(5)
    log_event(run_id="ctx", agent="pro", event_type="message", runs_dir=runs_dir)
    record = _read_lines(runs_dir / "ctx" / "ctx.jsonl")[0]
    assert record["round"] == 5

    clear_context()
    with pytest.raises(ValidationError):
        log_event(run_id="ctx", agent="pro", event_type="message", runs_dir=runs_dir)
    # The failed (unbound-round) emit added no further line.
    assert len(_read_lines(runs_dir / "ctx" / "ctx.jsonl")) == 1


def test_idempotent_get_logger_keeps_single_sink(tmp_path: Path) -> None:
    """Repeated ``get_logger`` between writes keeps one sink (no dup lines)."""
    runs_dir = tmp_path / "runs"
    log_event(run_id="idem", round=1, agent="pro", event_type="system", runs_dir=runs_dir)
    get_logger("idem", runs_dir=runs_dir)
    log_event(run_id="idem", round=2, agent="pro", event_type="system", runs_dir=runs_dir)

    records = _read_lines(runs_dir / "idem" / "idem.jsonl")
    assert [r["round"] for r in records] == [1, 2]
