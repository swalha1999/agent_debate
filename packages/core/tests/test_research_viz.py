"""Tests for the research visualization helpers (issue #99, task 14.3, PRD §9).

TDD-first: pin the 14.3 contract — chart helpers that take the 14.2 analysis
outputs and write non-empty PNG files to a caller-supplied directory. The Agg
backend is forced (headless, no display) inside the module, so these run cleanly
on CI/Windows. Synthetic in-memory fixtures only — never the committed sample
runs — so the assertions never depend on those files staying fixed. No network,
no key, no real run files.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.research import (
    RoundMetric,
    RunSummary,
    save_agree_disagree_chart,
    save_all_figures,
    save_nudges_chart,
    save_round_tokens_chart,
    save_who_wins_chart,
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


def _rounds() -> list[RoundMetric]:
    """Two synthetic round metrics with growing tokens/latency."""
    return [
        RoundMetric(round=1, tokens=300, latency_ms=30.0, pro_tokens=100, con_tokens=200),
        RoundMetric(round=2, tokens=700, latency_ms=70.0, pro_tokens=300, con_tokens=400),
    ]


def _assert_png(path: Path) -> None:
    """A real, non-empty PNG file was written at ``path``."""
    assert path.is_file()
    assert path.suffix == ".png"
    assert path.stat().st_size > 0


def test_save_who_wins_chart_writes_png(tmp_path: Path) -> None:
    """The who-wins chart is saved as a non-empty PNG in the out dir."""
    out = save_who_wins_chart(_rows(), tmp_path)
    _assert_png(out)


def test_save_agree_disagree_chart_writes_png(tmp_path: Path) -> None:
    """The agree-vs-disagree chart is saved as a non-empty PNG."""
    out = save_agree_disagree_chart(_rows(), tmp_path)
    _assert_png(out)


def test_save_nudges_chart_writes_png(tmp_path: Path) -> None:
    """The per-side drift/nudge chart is saved as a non-empty PNG."""
    out = save_nudges_chart(_rows(), tmp_path)
    _assert_png(out)


def test_save_round_tokens_chart_writes_png(tmp_path: Path) -> None:
    """The per-round tokens/latency chart is saved as a non-empty PNG."""
    out = save_round_tokens_chart(_rounds(), tmp_path, run_id="a")
    assert out is not None
    _assert_png(out)


def test_save_round_tokens_chart_empty_returns_none(tmp_path: Path) -> None:
    """No round metrics yields no file (None) rather than an empty chart."""
    assert save_round_tokens_chart([], tmp_path, run_id="a") is None


def test_save_all_figures_writes_every_chart(tmp_path: Path) -> None:
    """save_all_figures writes the four §9 charts and returns their paths."""
    paths = save_all_figures(_rows(), tmp_path, rounds=_rounds(), run_id="a")
    assert len(paths) == 4
    for path in paths:
        _assert_png(path)


def test_save_all_figures_skips_round_chart_without_rounds(tmp_path: Path) -> None:
    """Without round metrics, only the three run-level charts are produced."""
    paths = save_all_figures(_rows(), tmp_path)
    assert len(paths) == 3


def test_out_dir_is_created_when_missing(tmp_path: Path) -> None:
    """The chart helpers create the output directory if it does not exist."""
    nested = tmp_path / "figures" / "nested"
    out = save_who_wins_chart(_rows(), nested)
    _assert_png(out)
