"""Tests for the debate SETUP step (issue #47, task 6.2, orchestration §3.1).

TDD-first: these assert the §3.1 setup contract before :func:`setup_debate`
exists. Setup is the *preparation* step of a run — it does NOT run any model
call (no network); the actual model calls live in the loop (6.3) and route
through the API gatekeeper (Epic 13).

Setup must:

* receive/set the topic and **validate** it via the 7.2 security validator
  (reject abusive/oversized topics with the clear typed error);
* privately **assign** Pro = FOR and Con = AGAINST (a fixed, explicit, structured
  assignment using the :class:`DebateSide` constants — never hard-coded strings);
* instantiate the three agents (Pro, Con, Controller) + their three ISOLATED
  contexts wired to the topic, the Controller staying NEUTRAL — the setup carries
  NO controller stance/opinion field;
* LOG one ``system`` setup event (run_id, sanitised topic, the assignment) — and
  never log any controller stance (there is none).

All agents use a pydantic-ai ``TestModel`` (no network, no key); log assertions
use a ``tmp_path`` runs dir. The side assignment + caps are read from config /
the public constants / :class:`DebateSide`, never hard-coded.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from agent_debate.core import (
    DebateConfig,
    DebateSetup,
    DebateSide,
    Settings,
    setup_debate,
)
from agent_debate.core.constants import SETUP_EVENT_TAG, SETUP_LOG_EVENT_TYPE
from agent_debate.core.security import InvalidInputError
from pydantic_ai.models import Model
from pydantic_ai.models.test import TestModel

_TOPIC = "Should remote work be the default for office jobs?"


def _models() -> dict[object, Model]:
    """A fresh per-agent ``TestModel`` map (Pro/Con/Controller) — offline, no key."""
    return {
        DebateSide.PRO: TestModel(),
        DebateSide.CON: TestModel(),
        "controller": TestModel(),
    }


def _config() -> DebateConfig:
    """A config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(max_words=120))


def _setup(**kwargs: object) -> DebateSetup:
    """Build a setup with both debaters + controller on an injected ``TestModel``."""
    return setup_debate(_TOPIC, _config(), models=_models(), **kwargs)  # type: ignore[arg-type]


def test_setup_returns_validated_trimmed_topic() -> None:
    """The setup carries the topic, trimmed by the 7.2 validator."""
    setup = setup_debate(f"  {_TOPIC}  ", _config(), models=_models())
    assert setup.topic == _TOPIC


def test_setup_assigns_pro_for_and_con_against() -> None:
    """Pro is assigned FOR and Con AGAINST — a fixed, explicit mapping (§3.1)."""
    setup = _setup()
    assert setup.pro_side is DebateSide.PRO
    assert setup.con_side is DebateSide.CON
    assert setup.side_assignment == {
        DebateSide.PRO: "FOR",
        DebateSide.CON: "AGAINST",
    }


def test_setup_builds_three_agents_and_three_isolated_contexts() -> None:
    """Setup wires Pro/Con/Controller agents + three distinct, empty contexts."""
    setup = _setup()
    assert setup.pro_agent is not None
    assert setup.con_agent is not None
    assert setup.controller_agent is not None
    agents = {id(setup.pro_agent), id(setup.con_agent), id(setup.controller_agent)}
    assert len(agents) == 3
    contexts = setup.contexts
    ids = {id(contexts.pro), id(contexts.con), id(contexts.controller)}
    assert len(ids) == 3  # three distinct isolated contexts
    assert contexts.pro.history() == ()
    assert contexts.con.history() == ()
    assert contexts.controller.history() == ()


def test_setup_injects_topic_into_both_debater_system_prompts() -> None:
    """Each debater's system prompt states the actual motion (not just 'the topic')."""
    setup = _setup()
    for agent in (setup.pro_agent, setup.con_agent):
        prompt = "\n".join(agent._system_prompts)  # noqa: SLF001 - inspect static prompt
        assert _TOPIC in prompt


def test_setup_carries_no_controller_stance_field() -> None:
    """Controller neutrality: the setup exposes NO stance/opinion field at all."""
    setup = _setup()
    field_names = {f.name for f in dataclasses.fields(setup)}
    for leak in ("stance", "opinion", "winner", "controller_side", "lean", "bias"):
        assert leak not in field_names, f"controller stance leak: {leak!r}"


@pytest.mark.parametrize(
    "bad_topic",
    ["", "   ", "topic\x1bwith-escape", "x" * 100_000],
)
def test_setup_rejects_invalid_topic(bad_topic: str) -> None:
    """An empty / control-char / oversized topic raises the 7.2 validation error."""
    with pytest.raises(InvalidInputError):
        setup_debate(bad_topic, _config(), models=_models())


def test_setup_logs_system_event_with_topic_and_assignment(tmp_path: Path) -> None:
    """Setup emits one ``system`` event carrying the topic + side assignment."""
    runs_dir = Path(str(tmp_path))
    _setup(run_id="run-6-2", runs_dir=runs_dir)
    log_path = runs_dir / "run-6-2" / "run-6-2.jsonl"
    events = [json.loads(line) for line in log_path.read_text().splitlines()]
    setups = [
        e
        for e in events
        if e["event_type"] == SETUP_LOG_EVENT_TYPE and e["payload"].get("event") == SETUP_EVENT_TAG
    ]
    assert setups, "expected a debate-setup event"
    payload = setups[0]["payload"]
    assert payload["topic"] == _TOPIC
    assert payload["assignment"] == {"pro": "FOR", "con": "AGAINST"}


def test_setup_event_logs_no_controller_stance(tmp_path: Path) -> None:
    """The setup event must never carry a controller stance/opinion (neutrality)."""
    runs_dir = Path(str(tmp_path))
    _setup(run_id="run-6-2-neutral", runs_dir=runs_dir)
    text = (runs_dir / "run-6-2-neutral" / "run-6-2-neutral.jsonl").read_text().lower()
    for leak in ("stance", "opinion", '"winner"', "i think", "is right"):
        assert leak not in text, f"controller stance leaked in log: {leak!r}"


def test_setup_without_run_id_skips_logging(tmp_path: Path) -> None:
    """With no ``run_id`` setup still prepares state; it just does not log."""
    setup = _setup()
    assert setup.topic == _TOPIC
    assert not list(Path(str(tmp_path)).glob("*.jsonl"))
