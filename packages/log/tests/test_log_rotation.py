"""TDD tests for config-driven FIFO log-file rotation (issue #217, HW2 §8.6).

HW2 §8.6 mandates that built-in logs use **FIFO file rotation**: a capped
number of files, each with a maximum line count, with the *oldest* file dropped
first once the cap is exceeded. These tests are written RED-first against the
not-yet-existing rotation surface in :mod:`agent_debate.log`.

Design under test (documented in ``_rotation.py``):

* The live file is always ``<runs_dir>/<run_id>.jsonl`` (backward compatible:
  existing readers keep that path).
* When it reaches ``max_lines`` lines it rolls over: archives shift up
  (``<run_id>.1.jsonl`` is the most-recently-archived, higher indices = older),
  and the live file starts empty again.
* At most ``max_files`` files exist (live + archives); the OLDEST archive
  (highest index) is deleted first when the cap would be exceeded (FIFO).
* Every file remains valid JSONL with at most ``max_lines`` lines.

Small caps are injected via ``RotationConfig`` for fast, deterministic checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.log._rotation import (
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_LINES_PER_FILE,
    RotatingJsonlSink,
    RotationConfig,
    load_rotation_config,
)


def _files(runs_dir: Path, run_id: str) -> list[Path]:
    """Return all JSONL files for ``run_id`` under ``runs_dir`` (any sorting)."""
    return list(runs_dir.glob(f"{run_id}*.jsonl"))


def _write(sink: RotatingJsonlSink, count: int, start: int = 0) -> None:
    """Append ``count`` distinct JSON event lines to the sink."""
    for i in range(start, start + count):
        sink.write(json.dumps({"n": i}) + "\n")


def test_rollover_creates_new_file_at_max_lines(tmp_path: Path) -> None:
    """Writing more than ``max_lines`` rolls over to a fresh live file."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=5, max_lines_per_file=3)
    sink = RotatingJsonlSink(runs_dir / "run-r.jsonl", cfg)

    _write(sink, 3)
    assert _files(runs_dir, "run-r") == [runs_dir / "run-r.jsonl"]

    _write(sink, 1, start=3)  # forces a rollover
    sink.flush()
    names = {p.name for p in _files(runs_dir, "run-r")}
    assert names == {"run-r.jsonl", "run-r.1.jsonl"}


def test_live_file_path_is_unsuffixed(tmp_path: Path) -> None:
    """The current/live file always stays ``<run_id>.jsonl`` (backward compat)."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=4, max_lines_per_file=2)
    sink = RotatingJsonlSink(runs_dir / "run-live.jsonl", cfg)

    _write(sink, 5)
    sink.flush()
    live = runs_dir / "run-live.jsonl"
    assert live.exists()
    # Newest event is in the live (unsuffixed) file.
    lines = [ln for ln in live.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert json.loads(lines[-1])["n"] == 4


def test_file_count_never_exceeds_max_files(tmp_path: Path) -> None:
    """No matter how many lines are written, file count stays within the cap."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=3, max_lines_per_file=2)
    sink = RotatingJsonlSink(runs_dir / "run-cap.jsonl", cfg)

    _write(sink, 100)
    sink.flush()
    assert len(_files(runs_dir, "run-cap")) <= cfg.max_files


def test_oldest_file_dropped_first_fifo(tmp_path: Path) -> None:
    """The earliest events vanish (oldest file deleted) while recent remain."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=2, max_lines_per_file=2)
    sink = RotatingJsonlSink(runs_dir / "run-fifo.jsonl", cfg)

    _write(sink, 8)  # 4 segments worth, but only 2 files retained
    sink.flush()

    surviving: set[int] = set()
    for path in _files(runs_dir, "run-fifo"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                surviving.add(json.loads(line)["n"])
    # Earliest events are gone; the most recent ones survive (FIFO drop).
    assert 0 not in surviving
    assert 7 in surviving
    assert max(surviving) == 7


def test_max_files_one_keeps_exactly_one_file(tmp_path: Path) -> None:
    """With ``max_files=1`` only the live file survives every rollover (no ``.1``)."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=1, max_lines_per_file=2)
    sink = RotatingJsonlSink(runs_dir / "run-single.jsonl", cfg)

    _write(sink, 7)  # several rollovers; only the live file may remain
    sink.flush()

    files = _files(runs_dir, "run-single")
    assert files == [runs_dir / "run-single.jsonl"]

    live = runs_dir / "run-single.jsonl"
    lines = [ln for ln in live.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) <= cfg.max_lines_per_file
    values = [json.loads(line)["n"] for line in lines]  # valid JSONL
    assert values[-1] == 6  # most-recent event retained


def test_every_file_is_valid_jsonl_within_line_cap(tmp_path: Path) -> None:
    """Each retained file parses as JSONL and respects the per-file line cap."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=5, max_lines_per_file=4)
    sink = RotatingJsonlSink(runs_dir / "run-valid.jsonl", cfg)

    _write(sink, 17)
    sink.flush()
    for path in _files(runs_dir, "run-valid"):
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) <= cfg.max_lines_per_file
        for line in lines:
            json.loads(line)  # raises if not valid JSON


def test_no_rollover_below_cap_keeps_single_file(tmp_path: Path) -> None:
    """Below the per-file cap nothing rotates — one file, all events present."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    cfg = RotationConfig(version="t", max_files=10, max_lines_per_file=50)
    sink = RotatingJsonlSink(runs_dir / "run-one.jsonl", cfg)

    _write(sink, 10)
    sink.flush()
    assert _files(runs_dir, "run-one") == [runs_dir / "run-one.jsonl"]


def test_load_rotation_config_reads_repo_file() -> None:
    """The repo ``config/logging.json`` loads into a validated RotationConfig."""
    cfg = load_rotation_config()
    assert cfg.max_files > 0
    assert cfg.max_lines_per_file > 0
    assert cfg.version


def test_load_rotation_config_rejects_bad_values(tmp_path: Path) -> None:
    """A non-positive cap fails validation with a clear error."""
    bad = tmp_path / "logging.json"
    bad.write_text(
        json.dumps({"logging": {"version": "x", "max_files": 0, "max_lines_per_file": 5}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="logging.json"):
        load_rotation_config(bad)


def test_defaults_match_pdf_example() -> None:
    """The shipped defaults follow the PDF example (20 files x 500 lines)."""
    assert DEFAULT_MAX_FILES == 20
    assert DEFAULT_MAX_LINES_PER_FILE == 500
