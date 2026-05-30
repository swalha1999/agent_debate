"""Tests for the ``agent_debate.log`` event schema (TASKS.md 1.2, issue #17).

Written TDD-first. The :class:`~agent_debate.log.LogEvent` Pydantic model is the
typed shape every structured log record takes (PRD §5.8): it carries ``run_id``,
``ts``, ``round``, ``agent``, ``event_type`` (a strict ``Literal`` of the seven
allowed kinds), ``payload``, ``tokens`` and ``latency_ms``. Acceptance criteria
(issue #17): every allowed ``event_type`` constructs; a bad ``event_type`` is
rejected with a ``ValidationError``; the model serialises to a single-line JSON
string that round-trips back to the same data; required fields are enforced.
"""

from __future__ import annotations

import json

import pytest
from agent_debate.log import EVENT_TYPES, LogEvent
from pydantic import ValidationError


def _minimal(**overrides: object) -> dict[str, object]:
    """Return a valid minimal kwargs dict for ``LogEvent``, with overrides."""
    base: dict[str, object] = {
        "run_id": "run-1",
        "round": 1,
        "agent": "pro",
        "event_type": "message",
        "payload": {"text": "hi"},
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_each_allowed_event_type_constructs(event_type: str) -> None:
    """Every allowed ``event_type`` builds a valid model."""
    event = LogEvent(**_minimal(event_type=event_type))  # type: ignore[arg-type]
    assert event.event_type == event_type


def test_event_types_constant_matches_prd() -> None:
    """The exported tuple lists exactly the seven PRD §5.8 event kinds."""
    assert EVENT_TYPES == (
        "message",
        "tool_call",
        "nudge",
        "timeout",
        "retry",
        "verdict",
        "system",
    )


def test_invalid_event_type_is_rejected() -> None:
    """An unknown ``event_type`` raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        LogEvent(**_minimal(event_type="bogus"))  # type: ignore[arg-type]


@pytest.mark.parametrize("missing", ["run_id", "round", "agent", "event_type"])
def test_required_fields_are_enforced(missing: str) -> None:
    """Dropping a required field raises a ``ValidationError``."""
    kwargs = _minimal()
    del kwargs[missing]
    with pytest.raises(ValidationError):
        LogEvent(**kwargs)  # type: ignore[arg-type]


def test_optional_fields_default_to_none() -> None:
    """``tokens`` and ``latency_ms`` are optional and default to ``None``."""
    event = LogEvent(**_minimal())  # type: ignore[arg-type]
    assert event.tokens is None
    assert event.latency_ms is None


def test_ts_defaults_to_a_timestamp() -> None:
    """``ts`` is populated by default when not supplied."""
    event = LogEvent(**_minimal())  # type: ignore[arg-type]
    assert event.ts is not None


def test_to_jsonl_is_single_line_and_round_trips() -> None:
    """``to_jsonl`` yields one JSON line that round-trips to the same data."""
    event = LogEvent(
        **_minimal(  # type: ignore[arg-type]
            tokens=42,
            latency_ms=12.5,
        )
    )
    line = event.to_jsonl()

    assert "\n" not in line
    restored = LogEvent.model_validate(json.loads(line))
    assert restored == event


def test_to_jsonl_payload_preserved() -> None:
    """A structured payload survives the JSONL round-trip intact."""
    payload = {"text": "hello", "nested": {"k": [1, 2, 3]}}
    event = LogEvent(**_minimal(payload=payload))  # type: ignore[arg-type]

    restored = json.loads(event.to_jsonl())
    assert restored["payload"] == payload
