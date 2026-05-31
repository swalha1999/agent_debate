"""Tests for the debate endpoints (task 10.2, issue #69).

TDD: assert the ``POST /debates`` + ``GET /debates/{id}`` contract before the
code exists. Tests run with no network and no API key — the SDK runner is
substituted by a stub injected via ``app.state`` (see :func:`set_debate_runner`),
so a canned :class:`~agent_debate.core.DebateResult` is returned instantly.
"""

from __future__ import annotations

import agent_debate.api.debate_runner as runner_mod
import pytest
from agent_debate.api.app import create_app
from agent_debate.api.debate_runner import default_runner, set_debate_runner
from agent_debate.api.debate_store import DebateStatus
from agent_debate.core import DebateResult
from fastapi import FastAPI
from fastapi.testclient import TestClient

_TOPIC = "Should cities ban cars from downtown?"


def _canned_result(topic: str) -> DebateResult:
    """Return a minimal, valid :class:`DebateResult` for ``topic``."""
    return DebateResult(topic=topic)


def _stub_app() -> FastAPI:
    """Build an app whose runner returns a canned result with no network."""
    app = create_app()
    set_debate_runner(app, lambda topic, overrides: _canned_result(topic))
    return app


def test_post_debates_returns_run_id_and_status() -> None:
    """``POST /debates`` accepts a topic and returns a non-empty run_id."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": _TOPIC})

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["run_id"], str)
    assert body["run_id"]
    assert body["status"] in {DebateStatus.RUNNING, DebateStatus.DONE}


def test_get_debate_returns_status_and_result_when_done() -> None:
    """``GET /debates/{id}`` returns the status and the result once complete."""
    client = TestClient(_stub_app())
    run_id = client.post("/debates", json={"topic": _TOPIC}).json()["run_id"]

    response = client.get(f"/debates/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["status"] == DebateStatus.DONE
    assert body["result"]["topic"] == _TOPIC


def test_get_unknown_run_id_returns_404() -> None:
    """``GET /debates/{unknown}`` returns 404 for an unknown run_id."""
    client = TestClient(_stub_app())

    response = client.get("/debates/does-not-exist")

    assert response.status_code == 404


def test_invalid_oversized_topic_returns_4xx() -> None:
    """An oversized topic is rejected with a 4xx and a clear error message."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": "x" * 5000})

    assert response.status_code == 422
    assert "Topic" in response.text


def test_empty_topic_returns_4xx() -> None:
    """A whitespace-only topic is rejected with a 4xx."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": "   "})

    assert response.status_code == 422


def test_missing_topic_returns_422() -> None:
    """A request body without a topic field fails request validation."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={})

    assert response.status_code == 422


def test_overrides_are_passed_to_the_runner() -> None:
    """Optional config overrides reach the runner as a dict."""
    app = create_app()
    captured: dict[str, object] = {}

    def _runner(topic: str, overrides: dict[str, object]) -> DebateResult:
        captured.update(overrides)
        return _canned_result(topic)

    set_debate_runner(app, _runner)
    client = TestClient(app)

    client.post("/debates", json={"topic": _TOPIC, "rounds": 3, "max_words": 80})

    assert captured == {"rounds": 3, "max_words": 80}


def test_failed_run_is_reported() -> None:
    """A runner that raises marks the run failed and surfaces the status."""
    app = create_app()

    def _boom(topic: str, overrides: dict[str, object]) -> DebateResult:
        raise RuntimeError("debate blew up")

    set_debate_runner(app, _boom)
    client = TestClient(app)
    run_id = client.post("/debates", json={"topic": _TOPIC}).json()["run_id"]

    body = client.get(f"/debates/{run_id}").json()

    assert body["status"] == DebateStatus.FAILED
    assert body["result"] is None


def test_default_runner_drives_the_sdk_with_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``default_runner`` builds an engine from overridden settings and runs it.

    The SDK is stubbed so no model call is made: we assert the override is folded
    into the settings and the engine's ``run`` is invoked with the topic.
    """
    captured: dict[str, object] = {}

    class _FakeEngine:
        def __init__(self, config: object, *, settings: object) -> None:
            captured["rounds"] = settings.rounds  # type: ignore[attr-defined]

        def run(self, topic: str) -> DebateResult:
            captured["topic"] = topic
            return _canned_result(topic)

    monkeypatch.setattr(runner_mod, "DebateEngine", _FakeEngine)

    result = default_runner(_TOPIC, {"rounds": 2})

    assert result.topic == _TOPIC
    assert captured == {"rounds": 2, "topic": _TOPIC}
