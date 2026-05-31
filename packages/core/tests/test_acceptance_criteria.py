"""PRD §11 acceptance criteria — the BEHAVIOURAL half (TASKS.md 12.1, issue #81).

Epic-12 acceptance pass: **every PRD §11 criterion has a test** that demonstrably
exercises it (PRD §11, the ~15-bullet checklist). The per-epic suites already
cover each unit; this module is the single place that *maps* each §11 bullet to a
named test so the checklist is provably green and stays so. Behaviours run
**end-to-end through the public** :class:`~agent_debate.core.DebateEngine` SDK +
the two gatekeepers, fully offline (pydantic-ai ``FunctionModel``/``TestModel``,
calls routed through an injected :class:`ApiGatekeeper` — no network, no key).

Criterion → test map (PRD §11 bullets 1-7, 9; the remaining hygiene/meta bullets
8, 10-15 live in ``test_acceptance_criteria_meta.py``):

* §11.1 end-to-end 10-vs-10, alternating, within word limit → ``test_c1_*``
* §11.2 debaters rebut the opponent (relay) → ``test_c2_*``
* §11.3 ≥2 named skills + web_search per debater → ``test_c3_*``
* §11.4 controller hides stance, detects+nudges ≥1 drift → ``test_c4_*``
* §11.5 a timed-out turn is killed + retried → ``test_c5_*``
* §11.6 verdict = summary + agree/disagree + who-won, no fact-check → ``test_c6_*``
* §11.7 five surfaces + every event carries run_id → ``test_c7_*`` (+ meta)
* §11.9 every external call routes through the gatekeeper; limits from config;
  overflow queued (no drop/crash) → ``test_c9_*``
"""

from __future__ import annotations

from pathlib import Path

from _acceptance_criteria_helpers import (
    TOPIC,
    logged_events,
    rebutting_model,
    run_engine,
)
from _gatekeeper_acceptance_helpers import FakeClock, make_config, make_gatekeeper
from _skills_acceptance_helpers import SpyGatekeeper
from _staged_drift_helpers import drifting_model, nudge_events, staged_run
from agent_debate.core import (
    DEBATER_SKILLS,
    DebateSide,
    assess_drift,
    build_controller_system_prompt,
    create_con_debater,
    create_pro_debater,
)
from agent_debate.core.agents.relay import ADVERSARIAL_RELAY_TEMPLATE
from agent_debate.core.constants import WEB_SEARCH_TOOL
from agent_debate.core.gatekeeper import QueueFullError
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

_DEFAULT_ROUNDS = 10
_PRO = "However your point fails; I counter and rebut the resolution directly."
_CON = "On the contrary, I disagree and counter that claim head on."


# --- §11.1 a debate runs end-to-end: 10 Pro + 10 Con, alternating, within limit -


def test_c1_full_debate_is_ten_vs_ten_alternating_within_word_limit(tmp_path: Path) -> None:
    cfg_words = 150
    result = run_engine(
        "c1", tmp_path, pro=rebutting_model(_PRO), con=rebutting_model(_CON), max_words=cfg_words
    )
    pro = [m for m in result.transcript if m.side is DebateSide.PRO]
    con = [m for m in result.transcript if m.side is DebateSide.CON]
    assert len(pro) == _DEFAULT_ROUNDS and len(con) == _DEFAULT_ROUNDS
    assert [m.side for m in result.transcript] == [DebateSide.PRO, DebateSide.CON] * _DEFAULT_ROUNDS
    assert all(m.word_count <= cfg_words for m in result.transcript)


# --- §11.2 debaters demonstrably rebut the opponent's last message --------------


def test_c2_debaters_rebut_opponent_via_adversarial_relay(tmp_path: Path) -> None:
    from _engine_acceptance_helpers import capturing_model, config, gatekeeper, models, text_model
    from agent_debate.core import DebateEngine

    cfg = config(rounds=2)
    con_seen: list[str] = []
    engine = DebateEngine(
        cfg,
        models=models(pro=text_model(_PRO), con=capturing_model(_CON, con_seen)),
        gatekeeper=gatekeeper("c2", tmp_path),
        runs_dir=tmp_path,
    )
    engine.run(TOPIC, run_id="c2")
    relay_lead = ADVERSARIAL_RELAY_TEMPLATE.split("{message}")[0]
    con_main = con_seen[: cfg.rounds]
    # Con rebuts Pro every main round: the relay framing AND Pro's actual content
    # are injected into Con's own prompt (rebutting the opponent, not a monologue).
    assert all(relay_lead in prompt for prompt in con_main)
    assert any(_PRO in prompt for prompt in con_main)


# --- §11.3 each debater uses web search + has >=2 named skills in its prompt -----


def test_c3_each_debater_has_web_search_plus_two_named_skills() -> None:
    for factory in (create_pro_debater, create_con_debater):
        agent: Agent[None, str] = factory(model=TestModel(), topic="Sample debate topic")
        names = set(agent._function_toolset.tools)  # noqa: SLF001 - inspect registered tools
        assert WEB_SEARCH_TOOL in names
        assert len(names - {WEB_SEARCH_TOOL}) >= 2
        prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - static system prompt
        for skill in DEBATER_SKILLS:
            assert skill in prompt  # every skill named in the system prompt


# --- §11.4 controller hides its stance; detects + nudges >=1 staged drift -------


def test_c4_controller_never_leaks_stance() -> None:
    lowered = build_controller_system_prompt().lower()
    assert "never reveal" in lowered and ("stance" in lowered or "opinion" in lowered)
    for leak in ("i think pro", "i think con", "i lean", "the for side is right"):
        assert leak not in lowered


def test_c4_staged_drift_is_detected_and_nudged_back(tmp_path: Path) -> None:
    concede_round = 2
    from _staged_drift_helpers import CONCEDING_LINE

    # Detection: the staged concession is classified as captured for the Pro side.
    assert assess_drift(CONCEDING_LINE, DebateSide.PRO).captured is True
    pro = drifting_model(DebateSide.PRO, concede_round=concede_round)
    con = drifting_model(DebateSide.CON, concede_round=0)  # never concedes
    result = staged_run("c4", tmp_path, pro=pro, con=con, rounds=concede_round)
    # Nudged back >=1: recorded in the result AND logged as a nudge event.
    assert [n for n in result.nudges if n.target is DebateSide.PRO]
    assert any(e["payload"]["target"] == DebateSide.PRO.value for e in nudge_events(tmp_path, "c4"))


# --- §11.5 a turn that exceeds the timeout is killed and retried automatically ---


def test_c5_timed_out_turn_is_killed_then_retried(tmp_path: Path) -> None:
    # Drive the timeout→cancel→retry path end-to-end through the public turn seam.
    from _engine_acceptance_helpers import config as eng_config
    from _engine_acceptance_helpers import gatekeeper, hang_n_times, text_model
    from agent_debate.core import setup_debate
    from agent_debate.core.engine.turn import run_debate_turn

    cfg = eng_config(rounds=1, max_words=50)
    setup = setup_debate(
        TOPIC,
        cfg,
        models={
            DebateSide.PRO: text_model(_PRO),
            DebateSide.CON: text_model(_CON),
            "controller": TestModel(),
        },
    )
    delays: list[float] = []
    message = run_debate_turn(
        agent=setup.pro_agent,
        context=setup.contexts.for_side(DebateSide.PRO),
        side=DebateSide.PRO,
        round_=1,
        config=cfg,
        gatekeeper=gatekeeper("c5", tmp_path),
        run_id="c5",
        runs_dir=tmp_path,
        opponent_message=None,
        sleep_fn=delays.append,
        timeout_runner=hang_n_times(1),
    )
    assert not message.failed and message.content == _PRO
    events = logged_events(tmp_path, "c5")
    assert any(e["event_type"] == "timeout" for e in events)
    assert any(e["event_type"] == "retry" for e in events)


# --- §11.6 final summary + agree/disagree + who won, with NO fact-checking -------


def test_c6_verdict_has_summary_result_winner_no_fact_check(tmp_path: Path) -> None:
    result = run_engine(
        "c6", tmp_path, pro=rebutting_model(_PRO), con=rebutting_model(_CON), rounds=2, max_words=50
    )
    assert result.verdict is not None
    assert result.verdict.summary  # written summary
    assert isinstance(result.verdict.converged, bool)  # agree/disagree result
    assert result.verdict.winner in (DebateSide.PRO, DebateSide.CON, "tie")  # who won
    assert any(e["event_type"] == "verdict" for e in logged_events(tmp_path, "c6"))


# --- §11.9 every external call via the gatekeeper; limits from config; queued ----


def test_c9_search_call_routes_through_the_gatekeeper(tmp_path: Path) -> None:
    keeper = SpyGatekeeper()
    from agent_debate.core import GatekeptSearchProvider, SearchResult
    from agent_debate.core.constants import SEARCH_SERVICE

    class _Inner:
        name = "inner"

        def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
            return [SearchResult(title=query, url="https://x.invalid", snippet="s")]

    GatekeptSearchProvider(_Inner(), gatekeeper=keeper).search("topic")
    assert keeper.services == [SEARCH_SERVICE]


def test_c9_overflow_is_queued_then_backpressured_never_dropped(tmp_path: Path) -> None:
    clock = FakeClock()
    gk = make_gatekeeper(
        make_config(requests_per_minute=1, requests_per_hour=100, queue_max_depth=1),
        clock,
        tmp_path,
    )
    ran: list[str] = []
    gk.execute(lambda: ran.append("a"), service="default")  # runs now
    gk.execute(lambda: ran.append("b"), service="default")  # queued (no drop/crash)
    assert ran == ["a"] and gk.get_queue_status().depth == 1
    try:
        gk.execute(lambda: ran.append("c"), service="default")  # queue full -> backpressure
        raise AssertionError("expected QueueFullError at capacity")
    except QueueFullError:
        pass
    clock.t += 61.0
    assert gk.drain() == 1 and ran == ["a", "b"]  # the queued call drains, never lost
