"""Epic-1 acceptance tests for ``agent_debate.log`` (TASKS.md 1.5, issue #20).

These exercise the three acceptance areas end-to-end through the **public API**
(``agent_debate.log``) — proving the integrated behaviour rather than
re-testing module internals (which the 1.1–1.4 unit suites already cover):

* (a) an event is written to ``runs/<run_id>.jsonl`` and round-trips back into
  a :class:`~agent_debate.log.LogEvent`,
* (b) an invalid ``event_type`` is rejected before anything reaches the sink,
* (c) redaction hides a fake key in the on-disk JSONL.

The default ``runs`` directory name is read from the package's single source of
truth (:data:`~agent_debate.log.DEFAULT_RUNS_DIR`) — never hard-coded here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.log import (
    DEFAULT_RUNS_DIR,
    REDACTED,
    LogEvent,
    clear_context,
    log_event,
)
from pydantic import ValidationError

#: A clearly-fake Anthropic-style key (matches the redactor's ``sk-ant-…``
#: pattern) used to prove redaction; never a real secret.
_FAKE_KEY = "sk-ant-api03-FAKEKEYFAKEKEYFAKEKEYFAKEKEY0123456789"

#: Fields a structlog record carries that are not part of ``LogEvent``; dropped
#: when reconstructing the model from a raw on-disk line.
_WRAPPER_KEYS = ("event", "level")


@pytest.fixture(autouse=True)
def _reset_context() -> None:
    """Start each test with no bound contextvars (no cross-test leakage)."""
    clear_context()


def _read_lines(path: Path) -> list[dict[str, object]]:
    """Parse every non-blank JSONL line in ``path`` into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _to_log_event(record: dict[str, object]) -> LogEvent:
    """Reconstruct a :class:`LogEvent` from a raw on-disk structlog record.

    Maps structlog's ``timestamp`` onto the model's ``ts`` and drops the
    renderer-added wrapper keys so the round-trip targets the public schema.
    """
    fields = {k: v for k, v in record.items() if k not in _WRAPPER_KEYS}
    fields["ts"] = fields.pop("timestamp")
    return LogEvent.model_validate(fields)


def test_event_written_to_run_jsonl_and_round_trips(tmp_path: Path) -> None:
    """(a) A logged event lands in ``<runs>/<run_id>.jsonl`` and round-trips."""
    runs_dir = tmp_path / DEFAULT_RUNS_DIR
    emitted = log_event(
        run_id="acc-1",
        round=2,
        agent="pro",
        event_type="message",
        payload={"text": "hello", "nested": {"k": [1, 2, 3]}},
        tokens=42,
        latency_ms=12.5,
        runs_dir=runs_dir,
    )

    jsonl_path = runs_dir / "acc-1.jsonl"
    assert jsonl_path.exists()
    records = _read_lines(jsonl_path)
    assert len(records) == 1

    restored = _to_log_event(records[0])
    assert restored.run_id == emitted.run_id
    assert restored.round == emitted.round
    assert restored.agent == emitted.agent
    assert restored.event_type == emitted.event_type
    assert restored.payload == emitted.payload
    assert restored.tokens == emitted.tokens
    assert restored.latency_ms == emitted.latency_ms


def test_invalid_event_type_rejected_and_nothing_written(tmp_path: Path) -> None:
    """(b) A bad ``event_type`` raises and leaves no JSONL file behind."""
    runs_dir = tmp_path / DEFAULT_RUNS_DIR
    with pytest.raises(ValidationError):
        log_event(
            run_id="acc-2",
            round=1,
            agent="con",
            event_type="not-a-real-type",
            runs_dir=runs_dir,
        )
    assert not (runs_dir / "acc-2.jsonl").exists()


def test_redaction_hides_fake_key_in_jsonl(tmp_path: Path) -> None:
    """(c) A fake key in the payload is redacted in the on-disk JSONL."""
    runs_dir = tmp_path / DEFAULT_RUNS_DIR
    log_event(
        run_id="acc-3",
        round=1,
        agent="pro",
        event_type="tool_call",
        payload={"api_key": _FAKE_KEY, "note": f"value {_FAKE_KEY}"},
        runs_dir=runs_dir,
    )

    raw = (runs_dir / "acc-3.jsonl").read_text(encoding="utf-8")
    assert _FAKE_KEY not in raw
    assert REDACTED in raw

    record = _read_lines(runs_dir / "acc-3.jsonl")[0]
    assert record["payload"]["api_key"] == REDACTED  # type: ignore[index]
