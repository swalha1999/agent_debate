"""Shared fixtures for the event-streaming tests (issue #51, task 6.6).

Kept separate from ``test_event_stream.py`` so each file stays under the 150-line
guideline (PRD §3.2). Everything is offline: agents use a pydantic-ai
``FunctionModel`` (no network, no key); model calls route through an injected
:class:`~agent_debate.core.ApiGatekeeper`; the JSONL sink lives under ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.core import (
    ApiGatekeeper,
    DebateConfig,
    DebateSide,
    Settings,
    load_rate_limit_config,
)
from agent_debate.log import LogEvent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

TOPIC = "Should remote work be the default for office jobs?"

#: The gatekeeper (Epic 13) logs its own ``tool_call``/``retry``/``system`` events
#: from its OWN bound run_id — an infrastructure concern, not part of the engine's
#: debate event stream the CLI/API/UI render as turns. The engine stream is the
#: debate events (message/nudge/timeout/retry/system/word-limit); completeness is
#: asserted against the JSONL minus the gatekeeper's own infrastructure events.
GATEKEEPER_AGENT = "gatekeeper"


def config(*, rounds: int = 1, max_words: int = 50) -> DebateConfig:
    """A small config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def text_model(text: str) -> FunctionModel:
    """A model that always returns ``text`` regardless of the prompt."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def models(*, pro: Model, con: Model, controller: Model | None = None) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {
        DebateSide.PRO: pro,
        DebateSide.CON: con,
        "controller": controller or TestModel(),
    }


def spy_gatekeeper(run_id: str, runs_dir: Path) -> ApiGatekeeper:
    """A real gatekeeper wired to the per-run JSONL sink (no spying needed here)."""
    return ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)


def logged_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Read the run's JSONL log, excluding the gatekeeper's own infra events."""
    path = runs_dir / run_id / f"{run_id}.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return [e for e in events if e["agent"] != GATEKEEPER_AGENT]


def key(event: LogEvent | dict[str, Any]) -> tuple[Any, ...]:
    """A comparable identity for an event: type + round + agent (ts/payload vary)."""
    if isinstance(event, LogEvent):
        return (event.event_type, event.round, event.agent)
    return (event["event_type"], event["round"], event["agent"])


class BoomGatekeeper:
    """A gatekeeper whose ``execute`` raises a non-transient error (a caller bug)."""

    def execute(self, api_call, *args, service="default", **kwargs):  # type: ignore[no-untyped-def]
        raise ValueError("boom")
