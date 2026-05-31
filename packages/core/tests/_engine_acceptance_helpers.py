"""Shared fixtures for the Epic-6 engine acceptance tests (TASKS.md 6.9, issue #54).

Kept separate from ``test_engine_acceptance.py`` so each file stays under the
150-line guideline (PRD §3.2). Everything is offline: agents use a pydantic-ai
``FunctionModel`` (no network, no key); model calls route through an injected
:class:`~agent_debate.core.ApiGatekeeper`; the JSONL sink lives under ``tmp_path``.

The relay-capturing model records the prompt text every model call receives so a
test can assert the adversarial relay framing (5.6) is injected into the agent's
own context before generation. Caps (rounds/max_words) come from a
:class:`DebateConfig`, never hard-coded.
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
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

TOPIC = "Should remote work be the default for office jobs?"

#: The gatekeeper (Epic 13) logs its own infra events under its bound run_id —
#: not part of the debate event stream the CLI/API/UI render as turns. The engine
#: stream's completeness is asserted against the JSONL minus those infra events.
GATEKEEPER_AGENT = "gatekeeper"


def config(*, rounds: int = 10, max_words: int = 150) -> DebateConfig:
    """A config built from explicit settings (config-driven, no hard-coding)."""
    return DebateConfig.from_settings(Settings(rounds=rounds, max_words=max_words))


def text_model(text: str) -> FunctionModel:
    """A model that always returns ``text`` regardless of the prompt."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def capturing_model(text: str, seen: list[str]) -> FunctionModel:
    """Return ``text`` and append the latest user-prompt text to ``seen``."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(_last_user_text(messages))
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def message_capturing_model(text: str, captured: list[list[ModelMessage]]) -> FunctionModel:
    """Return ``text`` and append the FULL ``ModelMessage`` list of each call.

    Unlike :func:`capturing_model` (which records only the last user text), this
    records the complete message history the model receives so a test can assert
    the leading ``SystemPromptPart`` the engine now delivers on the history path.
    """

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        captured.append(list(messages))
        return ModelResponse(parts=[TextPart(content=text)])

    return FunctionModel(_fn)


def _last_user_text(messages: list[ModelMessage]) -> str:
    """Concatenate the text parts of the last ``ModelRequest`` (the live prompt)."""
    for message in reversed(messages):
        if isinstance(message, ModelRequest):
            return " ".join(
                getattr(part, "content", "")
                for part in message.parts
                if isinstance(getattr(part, "content", None), str)
            )
    return ""


def models(*, pro: Model, con: Model, controller: Model | None = None) -> dict[object, Model]:
    """Per-agent model map (Pro/Con/Controller) — offline, no key."""
    return {
        DebateSide.PRO: pro,
        DebateSide.CON: con,
        "controller": controller or TestModel(),
    }


def gatekeeper(run_id: str, runs_dir: Path) -> ApiGatekeeper:
    """A real gatekeeper wired to the per-run JSONL sink."""
    return ApiGatekeeper(load_rate_limit_config(), run_id=run_id, runs_dir=runs_dir)


class TimeoutGatekeeper:
    """A gatekeeper whose every ``execute`` raises a transient ``TimeoutError``.

    Drives the exhausted-retry path end-to-end through the SDK: with
    ``max_retries=0`` exhaustion is immediate, so the loop (which has no sleep
    seam) never sleeps and the whole debate still completes with FAILED turns.
    """

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        raise TimeoutError("model hung")


def logged_events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    """Read the run's JSONL log, excluding the gatekeeper's own infra events."""
    path = runs_dir / f"{run_id}.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    return [e for e in events if e["agent"] != GATEKEEPER_AGENT]


def key(event: LogEvent | dict[str, Any]) -> tuple[Any, ...]:
    """A comparable identity for an event: type + round + agent (ts/payload vary)."""
    if isinstance(event, LogEvent):
        return (event.event_type, event.round, event.agent)
    return (event["event_type"], event["round"], event["agent"])


def hang_n_times(n: int) -> Any:
    """A timeout-runner seam that raises ``TimeoutError`` the first ``n`` calls.

    Deterministic, fast: no real threads or timeouts. After ``n`` simulated
    timeouts the wrapped call runs normally, so a value of 1 exercises the
    cancel→retry→success path and a large value exhausts the retry budget.
    """
    state = {"left": n}

    def _runner(call: Any, timeout_s: float) -> Any:
        if state["left"] > 0:
            state["left"] -= 1
            raise TimeoutError(f"call exceeded {timeout_s}s")
        return call()

    return _runner
