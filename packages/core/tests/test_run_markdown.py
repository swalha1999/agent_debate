"""Tests for the readable run markdown exporter (task 12.5, PRD §10/§11, issue #86).

TDD-first: these assert the 12.5 contract — a readable ``runs/<run_id>.md`` rendered
from a completed :class:`DebateResult` carrying the transcript, the controller nudges,
the verdict and the cost-breakdown table. The cost table MUST reuse the existing
:func:`format_cost_table` renderer (no duplicated pricing/markdown), so a priced
result's table appears verbatim in the document. ``write_run_markdown`` writes the
document to ``<runs_dir>/<run_id>.md`` and returns the path. Rendering is pure (no
network, no key): the result is built in-memory.
"""

from __future__ import annotations

from pathlib import Path

from agent_debate.core import (
    CostBreakdown,
    DebateMessage,
    DebateResult,
    DebateSide,
    ModelCostRow,
    NudgeMessage,
    Verdict,
    format_cost_table,
    render_run_markdown,
    write_run_markdown,
)

_RUN_ID = "sample-run-0001"


def _result() -> DebateResult:
    breakdown = CostBreakdown(
        rows=[
            ModelCostRow(
                model="anthropic:claude-sonnet-4-6",
                input_tokens=1000,
                output_tokens=200,
                input_cost=0.003,
                output_cost=0.003,
                total_cost=0.006,
            )
        ],
        input_tokens=1000,
        output_tokens=200,
        total_cost=0.006,
    )
    return DebateResult(
        topic="Should cities ban cars downtown?",
        transcript=[
            DebateMessage(round=1, side=DebateSide.PRO, content="Cars waste scarce space."),
            DebateMessage(round=1, side=DebateSide.CON, content="Cars give people freedom."),
        ],
        nudges=[
            NudgeMessage(
                target=DebateSide.CON,
                reason="restated the opponent without rebuttal",
                correction="Defend your assigned side; rebut Pro's space claim.",
            )
        ],
        closing_discussion=[
            DebateMessage(round=1, side=DebateSide.PRO, content="In closing: reclaim the street."),
        ],
        verdict=Verdict(
            winner=DebateSide.PRO,
            rationale="Pro rebutted more directly.",
            scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
            summary="A lively exchange on urban space.",
            converged=False,
        ),
        cost_breakdown=breakdown,
    )


def test_markdown_has_topic_run_id_and_sections() -> None:
    md = render_run_markdown(_result(), run_id=_RUN_ID)
    assert _RUN_ID in md
    assert "Should cities ban cars downtown?" in md
    assert "## Transcript" in md
    assert "## Controller nudges" in md
    assert "## Verdict" in md
    assert "## Cost" in md


def test_markdown_includes_transcript_and_closing_content() -> None:
    md = render_run_markdown(_result(), run_id=_RUN_ID)
    assert "Cars waste scarce space." in md
    assert "Cars give people freedom." in md
    assert "In closing: reclaim the street." in md
    assert "## Closing discussion" in md


def test_markdown_includes_nudge_and_verdict_fields() -> None:
    md = render_run_markdown(_result(), run_id=_RUN_ID)
    assert "restated the opponent without rebuttal" in md
    assert "Defend your assigned side" in md
    assert "Pro rebutted more directly." in md
    assert "A lively exchange on urban space." in md
    # winner label is rendered
    assert "pro" in md.lower()


def test_markdown_reuses_format_cost_table_verbatim() -> None:
    result = _result()
    assert result.cost_breakdown is not None
    md = render_run_markdown(result, run_id=_RUN_ID)
    assert format_cost_table(result.cost_breakdown) in md


def test_markdown_handles_missing_verdict_and_cost() -> None:
    bare = DebateResult(topic="No verdict yet")
    md = render_run_markdown(bare, run_id=_RUN_ID)
    assert "No verdict yet" in md
    # No crash; the verdict/cost sections degrade gracefully.
    assert _RUN_ID in md


def test_write_run_markdown_writes_file(tmp_path: Path) -> None:
    path = write_run_markdown(_result(), run_id=_RUN_ID, runs_dir=tmp_path)
    assert path == tmp_path / f"{_RUN_ID}.md"
    text = path.read_text(encoding="utf-8")
    assert "## Transcript" in text
    assert "Cars waste scarce space." in text
