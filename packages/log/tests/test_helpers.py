"""Tests for the ``agent_debate.log`` helper API (TASKS.md 1.3, issue #18).

Written TDD-first. This task ties together the 1.1 setup factory and the 1.2
event schema into an ergonomic public surface (PRD §5.8):

* :func:`get_logger` returns a structlog logger bound to ``run_id`` (with the
  per-run JSONL sink configured) — idempotent across calls.
* :func:`log_event` builds and **validates** a :class:`LogEvent` (so an invalid
  ``event_type`` or missing field raises *before* anything is emitted) and then
  writes the validated record as one JSON line to ``runs/<run_id>.jsonl``.
* :func:`bind_round` / :func:`clear_context` bind a ``round`` (and other fields)
  into structlog's contextvars so they propagate to subsequent emitted events.

Acceptance criteria (issue #18): other packages can log structured events with
``run_id``/``round`` bound; ``get_logger(run_id)`` returns a bound logger;
``log_event(**fields)`` validates via ``LogEvent`` and emits a JSONL event.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.log import (
    bind_round,
    clear_context,
    get_logger,
    log_event,
)
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _reset_context() -> None:
    """Each test starts with no bound contextvars (no cross-test leakage)."""
    clear_context()


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_get_logger_binds_run_id(tmp_path: Path) -> None:
    """``get_logger`` returns a logger whose emissions carry ``run_id``."""
    runs_dir = tmp_path / "runs"
    logger = get_logger("run-1", runs_dir=runs_dir)
    logger.info("hi", event_type="system")

    records = _read_jsonl(runs_dir / "run-1" / "run-1.jsonl")
    assert records[0]["run_id"] == "run-1"


def test_log_event_writes_validated_json_line(tmp_path: Path) -> None:
    """A valid ``log_event`` writes one JSONL record with its fields."""
    runs_dir = tmp_path / "runs"
    log_event(
        run_id="run-2",
        round=3,
        agent="pro",
        event_type="message",
        payload={"text": "hello"},
        runs_dir=runs_dir,
    )

    records = _read_jsonl(runs_dir / "run-2" / "run-2.jsonl")
    assert len(records) == 1
    record = records[0]
    assert record["run_id"] == "run-2"
    assert record["round"] == 3
    assert record["event_type"] == "message"
    assert record["agent"] == "pro"
    assert record["payload"] == {"text": "hello"}


def test_log_event_invalid_event_type_raises_before_write(tmp_path: Path) -> None:
    """An invalid ``event_type`` raises and writes nothing to the sink."""
    runs_dir = tmp_path / "runs"
    with pytest.raises(ValidationError):
        log_event(
            run_id="run-3",
            round=1,
            agent="con",
            event_type="bogus",
            runs_dir=runs_dir,
        )

    assert not (runs_dir / "run-3" / "run-3.jsonl").exists()


def test_log_event_missing_field_raises(tmp_path: Path) -> None:
    """Omitting a required field raises a ``ValidationError`` before emit."""
    runs_dir = tmp_path / "runs"
    with pytest.raises(ValidationError):
        log_event(
            run_id="run-4",
            agent="pro",
            event_type="system",
            runs_dir=runs_dir,
        )


def test_bound_round_propagates_to_events(tmp_path: Path) -> None:
    """A round bound via ``bind_round`` shows up on later emitted events."""
    runs_dir = tmp_path / "runs"
    get_logger("run-5", runs_dir=runs_dir)
    bind_round(7)
    log_event(
        run_id="run-5",
        agent="pro",
        event_type="message",
        runs_dir=runs_dir,
    )

    records = _read_jsonl(runs_dir / "run-5" / "run-5.jsonl")
    assert records[0]["round"] == 7


def test_explicit_round_overrides_bound_round(tmp_path: Path) -> None:
    """An explicit ``round`` kwarg wins over the contextvar-bound round."""
    runs_dir = tmp_path / "runs"
    bind_round(1)
    log_event(
        run_id="run-6",
        round=9,
        agent="pro",
        event_type="message",
        runs_dir=runs_dir,
    )

    records = _read_jsonl(runs_dir / "run-6" / "run-6.jsonl")
    assert records[0]["round"] == 9


def test_clear_context_removes_bound_round(tmp_path: Path) -> None:
    """``clear_context`` drops the bound round so it no longer propagates."""
    runs_dir = tmp_path / "runs"
    bind_round(4)
    clear_context()
    with pytest.raises(ValidationError):
        log_event(
            run_id="run-7",
            agent="pro",
            event_type="message",
            runs_dir=runs_dir,
        )


def test_get_logger_is_idempotent(tmp_path: Path) -> None:
    """Repeated ``get_logger`` calls do not duplicate JSONL lines."""
    runs_dir = tmp_path / "runs"
    get_logger("run-8", runs_dir=runs_dir)
    logger = get_logger("run-8", runs_dir=runs_dir)
    logger.info("once", event_type="system")

    records = _read_jsonl(runs_dir / "run-8" / "run-8.jsonl")
    assert len(records) == 1


def test_log_event_carries_optional_cost_fields(tmp_path: Path) -> None:
    """``tokens`` and ``latency_ms`` pass through to the emitted record."""
    runs_dir = tmp_path / "runs"
    log_event(
        run_id="run-9",
        round=1,
        agent="con",
        event_type="tool_call",
        tokens=128,
        latency_ms=42.5,
        runs_dir=runs_dir,
    )

    record = _read_jsonl(runs_dir / "run-9" / "run-9.jsonl")[0]
    assert record["tokens"] == 128
    assert record["latency_ms"] == 42.5
