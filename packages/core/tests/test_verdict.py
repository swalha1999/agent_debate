"""Tests for the deepened verdict (TASKS.md 8.3, issue #62, PRD §3.2 step 4).

TDD-first: these assert the §3.2 verdict contract before :func:`render_verdict`
is deepened and wired into the engine. The controller writes a SUMMARY of the
debate, whether the agents AGREED/CONVERGED, the RESULT, and WHO WON with
REASONING — judged on ARGUMENTATION / REBUTTAL QUALITY / ENGAGEMENT, explicitly
**not** factual correctness (PRD §3: no fact-checking / truth verification).

The deterministic baseline scoring derives those three criteria from transparent,
named signals in the transcript text (rebuttal markers, engagement markers, turn
substance) — never from whether a claim is *true*. Constructed transcripts prove
the higher-engagement / more-rebutting side wins, a balanced debate ties, and no
truth-checking happens. The engine (:func:`run_debate_loop` / ``DebateEngine.run``
with ``TestModel``) populates ``DebateResult.verdict`` and logs a ``verdict`` event.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    DebateConfig,
    DebateResult,
    DebateSide,
    Settings,
    setup_debate,
)
from agent_debate.core.engine import run_debate_loop
from agent_debate.core.skills import TranscriptTurn, Verdict, render_verdict
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"


def _turn(side: str, text: str) -> TranscriptTurn:
    return TranscriptTurn(side=side, text=text)  # type: ignore[arg-type]


def test_verdict_has_summary_converged_winner_reasoning_scores() -> None:
    """The verdict carries a summary, a converged flag, a winner, reasoning, scores."""
    transcript = [
        _turn("pro", "Remote work boosts output. However the office model fails here."),
        _turn("con", "I disagree; offices build culture and counter that claim directly."),
    ]

    verdict = render_verdict(transcript)

    assert isinstance(verdict, Verdict)
    assert verdict.summary
    assert isinstance(verdict.converged, bool)
    assert verdict.winner in (DebateSide.PRO, DebateSide.CON, "tie")
    assert verdict.rationale
    assert set(verdict.scores) == {DebateSide.PRO, DebateSide.CON}
    assert set(verdict.criteria_scores) == {DebateSide.PRO, DebateSide.CON}


def test_verdict_winner_is_the_more_engaging_rebutting_side() -> None:
    """The side that rebuts and engages more wins — argumentation, not truth."""
    transcript = [
        # Pro: rebuts and engages repeatedly (markers: however, counter, disagree).
        _turn("pro", "However your point fails. I disagree and counter it directly."),
        _turn("pro", "On the contrary, that claim is flawed; I rebut it head on."),
        # Con: a flat assertion with no rebuttal/engagement signals.
        _turn("con", "Offices are nice places to be."),
    ]

    verdict = render_verdict(transcript)

    assert verdict.winner is DebateSide.PRO
    assert verdict.scores[DebateSide.PRO] > verdict.scores[DebateSide.CON]


def test_verdict_con_wins_when_con_out_argues_pro() -> None:
    """Symmetric: the higher-engagement con side wins."""
    transcript = [
        _turn("pro", "Remote work is good."),
        _turn("con", "However that fails. I disagree and counter it; the claim is flawed."),
        _turn("con", "On the contrary, I rebut that directly and it does not follow."),
    ]

    verdict = render_verdict(transcript)

    assert verdict.winner is DebateSide.CON


def test_verdict_balanced_debate_is_a_tie() -> None:
    """Two symmetric sides within the tie margin produce an explicit tie."""
    transcript = [
        _turn("pro", "However that fails. I disagree and counter it directly."),
        _turn("con", "However that fails. I disagree and counter it directly."),
    ]

    verdict = render_verdict(transcript)

    assert verdict.winner == "tie"


def test_verdict_does_not_fact_check() -> None:
    """A factually false but well-argued side still wins on argumentation alone."""
    # Pro states an obvious falsehood but rebuts/engages; con states a truth flatly.
    transcript = [
        _turn("pro", "The sky is green. However your point fails; I counter and disagree."),
        _turn("con", "The sky is blue."),
    ]

    verdict = render_verdict(transcript)

    # No truth-checking: the better-argued (false) side wins.
    assert verdict.winner is DebateSide.PRO


def test_verdict_converged_when_both_sides_concede() -> None:
    """Mutual agreement/concession signals mark the debate as converged."""
    transcript = [
        _turn("pro", "You're right, I agree with your point and accept that."),
        _turn("con", "I agree as well; that is a fair point and you're right."),
    ]

    verdict = render_verdict(transcript)

    assert verdict.converged is True


def test_verdict_round_trips_through_json() -> None:
    """The deepened ``Verdict`` is serialisable and reloads unchanged."""
    verdict = render_verdict([_turn("pro", "However I counter that."), _turn("con", "Fine.")])

    restored = Verdict.model_validate_json(verdict.model_dump_json())

    assert restored == verdict


# --- engine wiring -------------------------------------------------------------


def _config(*, rounds: int = 2, max_words: int = 50) -> DebateConfig:
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def _text_model(text: str) -> FunctionModel:
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _models(*, pro: Model, con: Model) -> dict[object, Model]:
    return {DebateSide.PRO: pro, DebateSide.CON: con, "controller": TestModel()}


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    path = runs_dir / f"{run_id}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_engine_populates_and_logs_verdict(tmp_path: Path) -> None:
    """run_debate_loop sets DebateResult.verdict and logs a ``verdict`` event."""
    runs_dir = Path(str(tmp_path))
    config = _config(rounds=1)
    setup = setup_debate(
        _TOPIC,
        config,
        models=_models(
            pro=_text_model("However your point fails; I counter and disagree."),
            con=_text_model("Offices are fine."),
        ),
    )

    result = run_debate_loop(setup, config, run_id="rv", runs_dir=runs_dir)

    assert isinstance(result, DebateResult)
    assert result.verdict is not None
    assert result.verdict.winner in (DebateSide.PRO, DebateSide.CON, "tie")
    assert result.verdict.summary
    verdict_events = [e for e in _events(runs_dir, "rv") if e["event_type"] == "verdict"]
    assert verdict_events, "expected a logged verdict event"
    assert verdict_events[0]["payload"].get("winner") in ("pro", "con", "tie")
