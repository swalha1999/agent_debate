"""Staged-drift fixture — §4 acceptance: drift is DETECTED and NUDGED back ≥1 (issue #63).

Anti-sycophancy ``docs/prds/anti-sycophancy.md`` §4 requires a STAGED drift fixture
(force an agent to PARROT/CONCEDE to the opponent) that is detected and nudged back
at least once. These tests drive a real conceding message — emitted deterministically
by the staged :func:`drifting_model` (no network) — through the public
:class:`~agent_debate.core.DebateEngine` SDK and assert end-to-end that:

* :func:`assess_drift` FLAGS the staged drift (``captured`` for that side);
* the controller NUDGES the agent back ≥1 (recorded in ``DebateResult.nudges`` AND
  logged as a ``nudge`` event in ``runs/<run_id>.jsonl``);
* the nudge is a PRIVATE correction, not a debate turn — the 10-vs-10 message
  invariant holds and the conceding line never appears in the opponent's transcript.

The on-side control (a non-drifting model yields ZERO nudges) is the red→green
guard: it proves the fixture's nudges come from the STAGED concession, not noise.
"""

from __future__ import annotations

from pathlib import Path

from _staged_drift_helpers import (
    CONCEDING_LINE,
    capturing_drifting_model,
    drifting_model,
    nudge_events,
    staged_run,
)
from agent_debate.core import DebateSide, assess_drift
from agent_debate.core.skills import NudgeMessage

CONCEDE_ROUND = 2


def test_assess_drift_flags_the_staged_concession() -> None:
    """The staged conceding line is classified as captured for the Pro side (§3/§4)."""
    assessment = assess_drift(CONCEDING_LINE, DebateSide.PRO)
    assert assessment.captured is True
    assert assessment.confidence >= 0.5


def test_staged_drift_is_detected_and_nudged_back(tmp_path: Path) -> None:
    """A debater forced to concede is nudged back ≥1 — recorded AND logged (§4)."""
    runs_dir = Path(str(tmp_path))
    pro = drifting_model(DebateSide.PRO, concede_round=CONCEDE_ROUND)
    con = drifting_model(DebateSide.CON, concede_round=0)  # never concedes
    result = staged_run("sd1", runs_dir, pro=pro, con=con, rounds=CONCEDE_ROUND)
    # The §4 acceptance: detected + nudged back at least once.
    assert len(result.nudges) >= 1
    pro_nudges = [n for n in result.nudges if n.target is DebateSide.PRO]
    assert len(pro_nudges) >= 1
    # The nudge is mirrored in the run's JSONL as a ``nudge`` event.
    logged = nudge_events(runs_dir, "sd1")
    assert any(e["payload"]["target"] == DebateSide.PRO.value for e in logged)


def test_nudge_is_private_not_a_debate_turn(tmp_path: Path) -> None:
    """The nudge is a PRIVATE correction; the 10-vs-10 invariant + isolation hold (§4)."""
    runs_dir = Path(str(tmp_path))
    pro = drifting_model(DebateSide.PRO, concede_round=CONCEDE_ROUND)
    con = drifting_model(DebateSide.CON, concede_round=0)
    result = staged_run("sd2", runs_dir, pro=pro, con=con, rounds=CONCEDE_ROUND)
    # Exactly ``rounds`` Pro + ``rounds`` Con messages — the nudge consumed no turn.
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == CONCEDE_ROUND
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == CONCEDE_ROUND
    assert all(isinstance(n, NudgeMessage) and n.is_debate_turn is False for n in result.nudges)
    # The private correction never leaks into the Con (opponent) transcript.
    con_text = " ".join(m.content for m in result.transcript if m.side is DebateSide.CON)
    assert all(n.correction not in con_text for n in result.nudges)


def test_on_side_debater_is_never_nudged(tmp_path: Path) -> None:
    """Control (red→green guard): a non-drifting debate yields ZERO nudges."""
    runs_dir = Path(str(tmp_path))
    pro = drifting_model(DebateSide.PRO, concede_round=0)  # never concedes
    con = drifting_model(DebateSide.CON, concede_round=0)
    result = staged_run("sd3", runs_dir, pro=pro, con=con, rounds=CONCEDE_ROUND)
    assert result.nudges == []
    assert nudge_events(runs_dir, "sd3") == []


def test_private_nudge_reaches_the_captured_agents_own_context(tmp_path: Path) -> None:
    """The correction is injected into the captured agent's OWN later prompt (§4)."""
    runs_dir = Path(str(tmp_path))
    pro_seen: list[str] = []
    pro = capturing_drifting_model(DebateSide.PRO, concede_round=1, seen=pro_seen)
    con = drifting_model(DebateSide.CON, concede_round=0)
    result = staged_run("sd4", runs_dir, pro=pro, con=con, rounds=CONCEDE_ROUND)
    assert result.nudges, "the staged concession must produce a nudge"
    correction = result.nudges[0].correction
    # Pro conceded on turn 1, so its round-2 prompt must carry the private moderator note.
    assert any(correction in prompt for prompt in pro_seen[1:])
