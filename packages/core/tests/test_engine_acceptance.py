"""Consolidated Epic-6 engine acceptance tests (TASKS.md 6.9, issue #54).

Orchestration sub-PRD ``docs/prds/debate-orchestration.md`` §7 acceptance criteria
exercised **end-to-end through the public** :class:`~agent_debate.core.DebateEngine`
**SDK** (mirroring how Epics 1/2/3/4/5/7/13 consolidated their acceptance pass).
The per-task suites cover each unit; this module proves the behaviours compose as
one story at the DEFAULT scale with a mocked LLM, NO network:

* a FULL debate at the default ``rounds`` (10) yields exactly 10 Pro + 10 Con
  messages, alternating, each ≤ ``max_words``;
* each Con/Pro message rebuts the opponent — the adversarial relay (5.6) framing
  is injected into the agent's own context before generation;
* a simulated TIMEOUT triggers cancel + retry (timeout + retry events), and the
  turn ultimately succeeds;
* an EXHAUSTED-retry turn is handled gracefully — marked FAILED, the controller
  informed, the debate completes without crashing;
* STREAMED events are ORDERED and COMPLETE vs the JSONL log.

Determinism: agents use a ``FunctionModel`` (offline, no key); model calls route
through an injected gatekeeper; the timeout/retry edges use the injectable
``timeout_runner``/``sleep_fn`` seams from :mod:`_call` so NO real sleeping or
threads occur. Caps come from a :class:`DebateConfig`, never hard-coded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _engine_acceptance_helpers import (
    TOPIC,
    TimeoutGatekeeper,
    capturing_model,
    config,
    gatekeeper,
    hang_n_times,
    key,
    logged_events,
    models,
    text_model,
)
from agent_debate.core import (
    DebateConfig,
    DebateEngine,
    DebateResult,
    DebateSide,
    Settings,
    setup_debate,
)
from agent_debate.core.agents.relay import ADVERSARIAL_RELAY_TEMPLATE
from agent_debate.core.engine.turn import run_debate_turn
from agent_debate.log import EVENT_TYPES, LogEvent

DEFAULT_ROUNDS = 10
_PRO_TEXT = "Pro affirms the resolution."
_CON_TEXT = "Con rebuts the resolution."


def _engine(rid: str, rdir: Path, *, cfg: DebateConfig, mdl: dict[object, Any]) -> DebateEngine:
    return DebateEngine(cfg, models=mdl, gatekeeper=gatekeeper(rid, rdir), runs_dir=rdir)


def test_full_default_debate_yields_ten_pro_ten_con(tmp_path: Path) -> None:
    """A FULL debate at the default rounds (10) yields exactly 10 Pro + 10 Con turns."""
    runs_dir = Path(str(tmp_path))
    cfg = config()  # default rounds=10, from settings (not hard-coded)
    assert cfg.rounds == DEFAULT_ROUNDS
    engine = _engine(
        "a1", runs_dir, cfg=cfg, mdl=models(pro=text_model(_PRO_TEXT), con=text_model(_CON_TEXT))
    )
    result = engine.run(TOPIC, run_id="a1")
    assert isinstance(result, DebateResult)
    assert len([m for m in result.transcript if m.side is DebateSide.PRO]) == DEFAULT_ROUNDS
    assert len([m for m in result.transcript if m.side is DebateSide.CON]) == DEFAULT_ROUNDS
    # Alternating Pro, Con, Pro, Con … across the whole main transcript.
    assert [m.side for m in result.transcript] == [DebateSide.PRO, DebateSide.CON] * DEFAULT_ROUNDS
    # Each main message is within the configured word limit (§5 enforcement).
    assert all(m.word_count <= cfg.max_words for m in result.transcript)


def test_each_message_rebuts_the_opponent_via_relay(tmp_path: Path) -> None:
    """From round 2 the adversarial relay (5.6) framing is injected before generation."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=2)
    pro_seen: list[str] = []
    con_seen: list[str] = []
    engine = _engine(
        "a2",
        runs_dir,
        cfg=cfg,
        mdl=models(
            pro=capturing_model(_PRO_TEXT, pro_seen), con=capturing_model(_CON_TEXT, con_seen)
        ),
    )
    engine.run(TOPIC, run_id="a2")
    relay_lead = ADVERSARIAL_RELAY_TEMPLATE.split("{message}")[0]
    # The first ``rounds`` prompts are the main debate turns; the trailing ones are
    # the (relay-free) closing statements — assert the relay over the main turns only.
    con_main = con_seen[: cfg.rounds]
    pro_main = pro_seen[: cfg.rounds]
    # Con rebuts Pro every main round (Pro always speaks first, so Con always has a
    # target); Pro rebuts from round 2 onward (no opponent message exists in round 1).
    assert all(relay_lead in prompt for prompt in con_main)
    assert all(relay_lead in prompt for prompt in pro_main[1:])
    assert relay_lead not in pro_main[0], "round-1 Pro has no opponent to rebut yet"
    # The opponent's actual content is quoted in the relay (the rebuttal target).
    assert any(_PRO_TEXT in prompt for prompt in con_main)


def test_simulated_timeout_triggers_cancel_then_retry(tmp_path: Path) -> None:
    """A turn whose call hangs once past the timeout cancels + retries, then succeeds."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=1, max_words=50)
    setup = setup_debate(
        TOPIC, cfg, models=models(pro=text_model(_PRO_TEXT), con=text_model(_CON_TEXT))
    )
    delays: list[float] = []
    message = run_debate_turn(
        agent=setup.pro_agent,
        context=setup.contexts.for_side(DebateSide.PRO),
        side=DebateSide.PRO,
        round_=1,
        config=cfg,
        gatekeeper=gatekeeper("a3", runs_dir),
        run_id="a3",
        runs_dir=runs_dir,
        opponent_message=None,
        sleep_fn=delays.append,  # injected: no real sleeping
        timeout_runner=hang_n_times(1),  # injected: no real threads/timeout
    )
    assert not message.failed
    assert message.content == _PRO_TEXT  # the retry reached the model and succeeded
    events = logged_events(runs_dir, "a3")
    assert any(e["event_type"] == "timeout" for e in events)
    assert any(e["event_type"] == "retry" for e in events)
    assert delays, "a backoff delay was scheduled via the injected sleep_fn (no real sleep)"


def test_exhausted_retry_turn_is_handled_gracefully(tmp_path: Path) -> None:
    """A turn that times out past every retry is marked FAILED; the controller is informed."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=1, max_words=50)
    setup = setup_debate(
        TOPIC, cfg, models=models(pro=text_model(_PRO_TEXT), con=text_model(_CON_TEXT))
    )
    delays: list[float] = []
    message = run_debate_turn(
        agent=setup.pro_agent,
        context=setup.contexts.for_side(DebateSide.PRO),
        side=DebateSide.PRO,
        round_=1,
        config=cfg,
        gatekeeper=gatekeeper("a4", runs_dir),
        run_id="a4",
        runs_dir=runs_dir,
        opponent_message=None,
        sleep_fn=delays.append,
        timeout_runner=hang_n_times(99),  # always times out -> budget exhausted
    )
    # The turn did not crash the caller: it returns a FAILED marker (graceful §4).
    assert message.failed
    events = logged_events(runs_dir, "a4")
    system = [e for e in events if e["event_type"] == "system"]
    assert any(e["payload"].get("turn_failed") for e in system), "controller must be informed"


def test_full_debate_survives_exhausted_turns(tmp_path: Path) -> None:
    """A whole debate whose calls always time out completes (no crash), all turns FAILED."""
    runs_dir = Path(str(tmp_path))
    # max_retries=0 -> exhaustion is immediate, so the loop (no sleep seam) never sleeps.
    cfg = DebateConfig.from_settings(Settings(rounds=2, max_words=50, max_retries=0))
    engine = DebateEngine(
        cfg,
        models=models(pro=text_model(_PRO_TEXT), con=text_model(_CON_TEXT)),
        gatekeeper=TimeoutGatekeeper(),
        runs_dir=runs_dir,
    )
    result = engine.run(TOPIC, run_id="a5")
    # The debate did NOT crash: every turn is recorded and marked FAILED (§4).
    assert isinstance(result, DebateResult)
    assert len(result.transcript) == cfg.rounds * 2
    assert all(m.failed for m in result.transcript)
    events = logged_events(runs_dir, "a5")
    assert any(e["event_type"] == "system" and e["payload"].get("turn_failed") for e in events)


def test_streamed_events_are_ordered_and_complete(tmp_path: Path) -> None:
    """``stream`` yields ordered, typed events; the sequence equals the JSONL log."""
    runs_dir = Path(str(tmp_path))
    cfg = config(rounds=2)
    engine = _engine(
        "a6", runs_dir, cfg=cfg, mdl=models(pro=text_model(_PRO_TEXT), con=text_model(_CON_TEXT))
    )
    events: list[LogEvent] = []
    result: DebateResult | None = None
    for item in engine.stream(TOPIC, run_id="a6"):
        if isinstance(item, LogEvent):
            events.append(item)
        else:
            result = item
    assert events, "stream should yield events"
    assert all(e.event_type in EVENT_TYPES for e in events)
    assert isinstance(result, DebateResult)
    assert [key(e) for e in events] == [key(e) for e in logged_events(runs_dir, "a6")]
