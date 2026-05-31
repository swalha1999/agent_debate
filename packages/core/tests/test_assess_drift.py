"""Deepened ``assess_drift`` drift-detector tests (TASKS.md 8.1, issue #60).

TDD red-first contract for Epic 8.1, which deepens the *baseline* drift detector
(``4.4``) into a robust, deterministic classifier of the four anti-sycophancy §3
drift signals: adopting the opponent's framing/conclusion, conceding the core
claim, hedging away from the assigned side, and restating the opponent without
rebuttal. The classifier is pure — no LLM/network call — so the API gatekeeper
(Epic 13) is N/A here; the controller LLM may still pass explicit ``signals``.

The public ``assess_drift`` / :class:`DriftAssessment` contract is held stable
(the 4.4 tests in ``test_controller_skills.py`` and the engine drift tests in
``test_debate_loop.py`` must stay green); these tests pin the *deeper* behaviour
on top of it: weighted confidence in ``[0, 1]``, a named capture threshold, a
human-readable reason naming the fired signal(s), and the optional opponent
context that surfaces "restating without rebuttal".
"""

from __future__ import annotations

from agent_debate.core import DebateSide, DriftAssessment, assess_drift
from agent_debate.core.skills._drift_constants import DRIFT_CAPTURE_THRESHOLD


def test_firm_on_side_message_is_not_captured_low_confidence() -> None:
    """A firm, on-side rebuttal is not captured and carries low confidence."""
    result = assess_drift(
        "That claim fails. The evidence shows the pro side still holds, however, "
        "because the data contradicts the opponent's assumption.",
        "pro",
    )

    assert isinstance(result, DriftAssessment)
    assert result.captured is False
    assert result.confidence < DRIFT_CAPTURE_THRESHOLD
    assert 0.0 <= result.confidence <= 1.0


def test_conceding_message_is_captured_high_confidence_reason_names_concession() -> None:
    """A clearly-conceding message is captured with high confidence; reason names it."""
    result = assess_drift("You're right, I concede the core claim entirely.", "pro")

    assert result.captured is True
    assert result.confidence >= DRIFT_CAPTURE_THRESHOLD
    assert "concede" in result.reason.lower() or "concession" in result.reason.lower()
    assert 0.0 <= result.confidence <= 1.0


def test_agreement_marker_is_captured() -> None:
    """An agreement marker ("fair point", "I agree") fires the capture verdict."""
    result = assess_drift("That's a fair point, and I agree it weighs against my side.", "con")

    assert result.captured is True
    assert result.confidence >= DRIFT_CAPTURE_THRESHOLD


def test_hedging_message_elevates_confidence_and_is_captured() -> None:
    """Hedging away from the assigned side raises confidence into capture range."""
    result = assess_drift(
        "Perhaps the opponent has a point, and it's true that their view may hold.",
        "pro",
    )

    assert result.captured is True
    assert result.confidence >= DRIFT_CAPTURE_THRESHOLD


def test_restating_opponent_without_rebuttal_is_captured_with_opponent_context() -> None:
    """High overlap with the opponent + no rebuttal marker => captured (given context)."""
    opponent = (
        "Renewable energy reduces emissions, creates green jobs, and lowers grid costs "
        "over the long run for every nation that adopts it."
    )
    restated = (
        "Renewable energy reduces emissions, creates green jobs, and lowers grid costs "
        "over the long run for every nation that adopts it indeed."
    )
    result = assess_drift(restated, "con", opponent_message=opponent)

    assert result.captured is True
    assert result.confidence >= DRIFT_CAPTURE_THRESHOLD
    assert "restat" in result.reason.lower() or "overlap" in result.reason.lower()


def test_rebutting_an_overlapping_message_is_not_flagged_as_restating() -> None:
    """High overlap is NOT capture when a clear rebuttal/counter marker is present."""
    opponent = (
        "Renewable energy reduces emissions, creates green jobs, and lowers grid costs "
        "over the long run for every nation that adopts it."
    )
    rebuttal = (
        "Renewable energy reduces emissions, but creates green jobs only briefly and "
        "raises grid costs; however, this does not hold because storage is unsolved."
    )
    result = assess_drift(rebuttal, "con", opponent_message=opponent)

    assert result.captured is False
    assert 0.0 <= result.confidence <= 1.0


def test_confidence_always_within_unit_interval() -> None:
    """Even when many signals fire at once, confidence is clamped into ``[0, 1]``."""
    opponent = "The opponent says taxes are good, fair, and right for everyone always."
    piled = (
        "You're right, I agree and I concede. Perhaps the opponent has a point; it's "
        "true that taxes are good, fair, and right for everyone always."
    )
    result = assess_drift(piled, "con", opponent_message=opponent, signals=["adopts_framing"])

    assert result.captured is True
    assert result.confidence <= 1.0
    assert result.confidence >= 0.0


def test_threshold_governs_capture() -> None:
    """``captured`` is exactly ``confidence >= DRIFT_CAPTURE_THRESHOLD``."""
    captured = assess_drift("I concede the point.", "pro")
    clean = assess_drift("The pro side holds firmly on the merits of the evidence.", "pro")

    assert captured.captured == (captured.confidence >= DRIFT_CAPTURE_THRESHOLD)
    assert clean.captured == (clean.confidence >= DRIFT_CAPTURE_THRESHOLD)


def test_reason_is_human_readable() -> None:
    """The reason is a non-trivial human-readable sentence, not a bare code."""
    result = assess_drift("Fair point, I accept that.", "con")

    assert result.reason.endswith(".")
    assert " " in result.reason.strip()


def test_caller_signals_still_force_capture_contract_stable() -> None:
    """The 4.4 contract holds: explicit controller signals still force capture."""
    result = assess_drift("A neutral message.", "con", signals=["adopts_opponent_framing"])

    assert result.captured is True
    assert result.confidence >= DRIFT_CAPTURE_THRESHOLD
    assert "adopts_opponent_framing" in result.reason


def test_opponent_context_is_optional_and_defaults_none() -> None:
    """Omitting opponent context keeps the text-only heuristic working (back-compat)."""
    result = assess_drift("I concede the core claim.", DebateSide.PRO)

    assert result.captured is True


def test_opponent_with_no_content_words_never_triggers_restating() -> None:
    """A short opponent message with no content tokens cannot fire the overlap signal."""
    result = assess_drift(
        "The pro side firmly holds on the strength of the evidence presented.",
        "pro",
        opponent_message="of to in on at",
    )

    assert result.captured is False
