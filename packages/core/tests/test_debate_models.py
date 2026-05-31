"""Tests for the Epic-6 typed engine models (issue #46, task 6.1).

TDD-first: these assert the orchestration sub-PRD §2 contract before the models
exist. They cover (a) :class:`DebateConfig` is **config-driven** — built from a
:class:`~agent_debate.core.Settings` instance so changing a setting changes the
config (no hard-coded defaults); (b) :class:`DebateConfig` validates its bounds;
(c) :class:`DebateResult` composes a transcript, tool calls, nudges, a closing
discussion, a verdict and token/cost/latency totals, reusing the existing
:class:`NudgeMessage` / :class:`Verdict` skills models; (d) the aggregate totals
sum correctly; and (e) everything serialises to JSON and round-trips.

This task is the typed MODELS only — the 10-vs-10 loop is later tasks (6.2+).
"""

from __future__ import annotations

import pytest
from agent_debate.core import (
    CostTotals,
    DebateConfig,
    DebateMessage,
    DebateResult,
    DebateSide,
    NudgeMessage,
    Settings,
    ToolCallRecord,
    Verdict,
)
from pydantic import ValidationError

#: A fully-valid DebateConfig payload; bounds tests override one field at a time.
_VALID_CONFIG: dict[str, object] = {
    "rounds": 10,
    "max_words": 150,
    "turn_timeout_s": 60,
    "max_retries": 2,
    "debater_model": "anthropic:d",
    "controller_model": "anthropic:c",
    "pro_model": "anthropic:d",
    "con_model": "anthropic:d",
}


def _settings(
    *,
    rounds: int = 7,
    max_words: int = 99,
    turn_timeout_s: int = 42,
    max_retries: int = 5,
    debater_model: str = "anthropic:dbtr",
    controller_model: str = "anthropic:ctrl",
) -> Settings:
    """A :class:`Settings` built with explicit, non-default-looking values."""
    return Settings(
        rounds=rounds,
        max_words=max_words,
        turn_timeout_s=turn_timeout_s,
        max_retries=max_retries,
        debater_model=debater_model,
        controller_model=controller_model,
    )


def test_config_from_settings_is_config_driven() -> None:
    """``from_settings`` copies every tunable from settings, not a constant."""
    config = DebateConfig.from_settings(_settings())
    assert config.rounds == 7
    assert config.max_words == 99
    assert config.turn_timeout_s == 42
    assert config.max_retries == 5
    assert config.debater_model == "anthropic:dbtr"
    assert config.controller_model == "anthropic:ctrl"


def test_config_tracks_setting_changes() -> None:
    """Changing a setting changes the derived config (no frozen default)."""
    low = DebateConfig.from_settings(_settings(rounds=3))
    high = DebateConfig.from_settings(_settings(rounds=12))
    assert low.rounds == 3
    assert high.rounds == 12


def test_config_resolves_per_side_model_overrides() -> None:
    """PRO/CON models follow the settings' resolved per-side fallback."""
    default = DebateConfig.from_settings(_settings())
    assert default.pro_model == "anthropic:dbtr"
    assert default.con_model == "anthropic:dbtr"
    overridden = DebateConfig.from_settings(
        Settings(debater_model="anthropic:dbtr", PRO_MODEL="anthropic:pro")
    )
    assert overridden.pro_model == "anthropic:pro"
    assert overridden.con_model == "anthropic:dbtr"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rounds", 0),
        ("rounds", -1),
        ("max_words", 0),
        ("turn_timeout_s", 0),
        ("max_retries", -1),
    ],
)
def test_config_rejects_non_positive_bounds(field: str, value: int) -> None:
    """rounds/max_words/timeout must be > 0; retries must be >= 0."""
    with pytest.raises(ValidationError):
        DebateConfig.model_validate({**_VALID_CONFIG, field: value})


def test_cost_totals_aggregate_from_messages() -> None:
    """``CostTotals.from_messages`` sums tokens, cost and latency per turn."""
    pro = DebateMessage(
        round=1,
        side=DebateSide.PRO,
        content="Pro.",
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.01,
        latency_ms=100.0,
    )
    con = DebateMessage(
        round=1,
        side=DebateSide.CON,
        content="Con.",
        input_tokens=20,
        output_tokens=7,
        cost_usd=0.02,
        latency_ms=150.0,
    )
    totals = CostTotals.from_messages([pro, con])
    assert totals.input_tokens == 30
    assert totals.output_tokens == 12
    assert totals.total_tokens == 42
    assert totals.cost_usd == pytest.approx(0.03)
    assert totals.latency_ms == pytest.approx(250.0)


def test_message_counts_words_from_content() -> None:
    """A :class:`DebateMessage` derives its ``word_count`` from content."""
    msg = DebateMessage(round=2, side=DebateSide.PRO, content="one two three")
    assert msg.word_count == 3


def _verdict() -> Verdict:
    return Verdict(
        winner=DebateSide.PRO,
        rationale="Pro tallied higher.",
        scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
    )


def _result() -> DebateResult:
    transcript = [
        DebateMessage(round=1, side=DebateSide.PRO, content="Pro point.", output_tokens=4),
        DebateMessage(round=1, side=DebateSide.CON, content="Con rebuttal.", output_tokens=6),
    ]
    closing = [DebateMessage(round=11, side=DebateSide.PRO, content="Closing word.")]
    return DebateResult(
        topic="Cats vs dogs",
        transcript=transcript,
        tool_calls=[
            ToolCallRecord(round=1, side=DebateSide.PRO, tool="search", arguments={"q": "x"})
        ],
        nudges=[NudgeMessage(target=DebateSide.CON, reason="drift", correction="Hold your side.")],
        closing_discussion=closing,
        verdict=_verdict(),
        totals=CostTotals.from_messages(transcript),
    )


def test_result_composes_full_debate() -> None:
    """A result holds transcript, tool calls, nudges, closing, verdict, totals."""
    result = _result()
    assert len(result.transcript) == 2
    assert result.tool_calls[0].tool == "search"
    assert result.nudges[0].target is DebateSide.CON
    assert result.closing_discussion[0].content == "Closing word."
    assert result.verdict is not None
    assert result.verdict.winner is DebateSide.PRO
    assert result.totals.total_tokens == 10


def test_result_verdict_is_optional() -> None:
    """A result may be constructed before the verdict is rendered."""
    result = DebateResult(topic="t")
    assert result.verdict is None
    assert result.transcript == []
    assert result.totals.total_tokens == 0


def test_result_round_trips_through_json() -> None:
    """The whole result serialises to JSON and validates back to an equal model."""
    result = _result()
    restored = DebateResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.verdict is not None
    assert restored.nudges[0].correction == "Hold your side."


def test_config_round_trips_through_json() -> None:
    """The config serialises to JSON and validates back to an equal model."""
    config = DebateConfig.from_settings(_settings())
    assert DebateConfig.model_validate_json(config.model_dump_json()) == config
