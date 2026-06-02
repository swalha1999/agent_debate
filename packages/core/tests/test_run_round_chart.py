"""Tests for the per-run round-token chart + Markdown embedding (PRD §9).

Pins the contract for the per-debate round-token charts that live beside each
run's transcript: :func:`save_run_round_tokens_chart` writes a non-empty PNG at
an exact caller path, and :func:`embed_round_chart_section` splices a
``## Round-by-round token usage`` section into the ``.md`` with a same-folder
relative image reference — idempotently. Synthetic in-memory fixtures only; no
network, no key, no committed run files.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core.research import (
    SECTION_HEADING,
    RoundMetric,
    embed_round_chart_section,
    save_run_round_tokens_chart,
)


def _rounds() -> list[RoundMetric]:
    """Three synthetic round metrics with a pro/con token split."""
    return [
        RoundMetric(round=1, tokens=300, latency_ms=30.0, pro_tokens=100, con_tokens=200),
        RoundMetric(round=2, tokens=700, latency_ms=70.0, pro_tokens=300, con_tokens=400),
        RoundMetric(round=3, tokens=500, latency_ms=50.0, pro_tokens=250, con_tokens=250),
    ]


def test_save_run_round_tokens_chart_writes_png(tmp_path: Path) -> None:
    """A non-empty PNG is written at the exact caller-supplied path."""
    out = tmp_path / "demo" / "demo-round-tokens.png"
    result = save_run_round_tokens_chart(_rounds(), out, "demo")
    assert result == out
    assert out.is_file()
    assert out.stat().st_size > 0


def test_embed_section_inserts_with_relative_reference() -> None:
    """The section is appended with a bare same-folder image filename."""
    md = "# Title\n\nbody\n"
    out = embed_round_chart_section(md, "demo-round-tokens.png")
    assert SECTION_HEADING in out
    assert "![Round-by-round token usage](demo-round-tokens.png)" in out
    assert out.startswith("# Title")


def test_embed_section_is_idempotent() -> None:
    """Embedding twice does not duplicate the section."""
    md = "# Title\n\nbody\n"
    once = embed_round_chart_section(md, "demo-round-tokens.png")
    twice = embed_round_chart_section(once, "demo-round-tokens.png")
    assert once == twice
    assert twice.count(SECTION_HEADING) == 1


def test_embed_section_replaces_stale_reference() -> None:
    """A stale image reference is replaced, not duplicated, on re-run."""
    md = "# Title\n\nbody\n"
    stale = embed_round_chart_section(md, "old-round-tokens.png")
    fresh = embed_round_chart_section(stale, "new-round-tokens.png")
    assert fresh.count(SECTION_HEADING) == 1
    assert "new-round-tokens.png" in fresh
    assert "old-round-tokens.png" not in fresh
