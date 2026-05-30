"""Tests for the ``agent_debate.log`` structlog setup factory (TASKS.md 1.1).

These are written TDD-first: ``configure(run_id, runs_dir=...)`` must wire
structlog with two sinks — a human-readable console renderer AND a per-run JSONL
file at ``<runs_dir>/<run_id>.jsonl`` — and be idempotent. The acceptance
criteria (issue #16): a configured logger writes both sinks, and calling
``configure`` twice neither errors nor duplicates output.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.log import configure
from agent_debate.log._setup import _DualSinkRenderer


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    """Parse every non-blank line of a JSONL file into a list of dicts."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_configure_creates_jsonl_file(tmp_path: Path) -> None:
    """The JSONL sink file is created under the given runs dir for the run id."""
    runs_dir = tmp_path / "runs"
    logger = configure("run-abc", runs_dir=runs_dir)
    logger.info("hello", event_type="system")

    jsonl_path = runs_dir / "run-abc.jsonl"
    assert jsonl_path.exists()


def test_configure_creates_missing_runs_dir(tmp_path: Path) -> None:
    """A non-existent runs dir is created rather than raising."""
    runs_dir = tmp_path / "deep" / "nested" / "runs"
    configure("run-xyz", runs_dir=runs_dir)
    assert runs_dir.is_dir()


def test_emitted_event_is_valid_json_line(tmp_path: Path) -> None:
    """An emitted event lands as a valid JSON object carrying its fields."""
    runs_dir = tmp_path / "runs"
    logger = configure("run-1", runs_dir=runs_dir)
    logger.info("a message", event_type="message", round=2)

    records = _read_jsonl(runs_dir / "run-1.jsonl")
    assert len(records) == 1
    record = records[0]
    assert record["event"] == "a message"
    assert record["event_type"] == "message"
    assert record["round"] == 2


def test_configure_returns_console_sink(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The console sink renders the event to stdout (human-readable)."""
    logger = configure("run-c", runs_dir=tmp_path / "runs")
    logger.info("console-visible", event_type="system")

    captured = capsys.readouterr()
    assert "console-visible" in captured.out


def test_configure_is_idempotent_no_duplicate_lines(tmp_path: Path) -> None:
    """Calling configure twice for a run does not duplicate JSONL output."""
    runs_dir = tmp_path / "runs"
    configure("run-dup", runs_dir=runs_dir)
    logger = configure("run-dup", runs_dir=runs_dir)
    logger.info("once", event_type="system")

    records = _read_jsonl(runs_dir / "run-dup.jsonl")
    assert len(records) == 1


def test_dual_sink_renderer_decodes_bytes_json(tmp_path: Path) -> None:
    """A bytes-returning JSON renderer is decoded before hitting the text sink."""
    sink_path = tmp_path / "out.jsonl"
    with sink_path.open("a", encoding="utf-8") as handle:
        renderer = _DualSinkRenderer(handle)
        renderer._json = lambda _logger, _method, ed: json.dumps(ed).encode("utf-8")  # type: ignore[assignment]
        result = renderer(None, "info", {"event": "bytes-path"})
    assert result == ""
    assert "bytes-path" in sink_path.read_text(encoding="utf-8")


def test_configure_default_runs_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With no runs_dir the default ('runs/') is used, relative to cwd."""
    monkeypatch.chdir(tmp_path)
    configure("run-default")
    assert (tmp_path / "runs" / "run-default.jsonl").exists() or (tmp_path / "runs").is_dir()
