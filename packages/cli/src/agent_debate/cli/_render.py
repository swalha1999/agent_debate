"""Readable console rendering of a :class:`DebateResult` (task 9.1, issue #64).

Split out of :mod:`agent_debate.cli.app` (PRD §3.2: split, don't compress) so the
command stays thin. 9.1 only needs a basic readable print of the transcript +
verdict — live streaming is 9.2 and ``--json`` is 9.3, so this stays plain.
"""

from __future__ import annotations

from agent_debate.core.engine.result import DebateMessage, DebateResult


def _format_turn(turn: DebateMessage) -> str:
    """One transcript line: ``[round N] side: content`` (failed turns flagged)."""
    marker = " (failed)" if turn.failed else ""
    return f"[round {turn.round}] {turn.side.value}{marker}: {turn.content}"


def render_result(result: DebateResult) -> str:
    """Return a plain, readable transcript + verdict block for ``result``."""
    lines = [f"Topic: {result.topic}", "", "Transcript:"]
    lines.extend(_format_turn(turn) for turn in result.transcript)
    if result.closing_discussion:
        lines.append("")
        lines.append("Closing discussion:")
        lines.extend(_format_turn(turn) for turn in result.closing_discussion)
    lines.append("")
    verdict = result.verdict
    if verdict is None:
        lines.append("Verdict: (none)")
    else:
        # ``winner`` is always a decisive DebateSide — a tie is forbidden (issue #215).
        lines.append(f"Verdict: winner={verdict.winner.value}")
        if verdict.summary:
            lines.append(f"Summary: {verdict.summary}")
        lines.append(f"Rationale: {verdict.rationale}")
    return "\n".join(lines)


__all__ = ["render_result"]
