"""Tests for API hardening — validation, error schema, CORS (task 10.4, #71).

TDD: assert the consistent error envelope, the CORS behaviour and the tightened
request validation *before* the code exists. All tests run with NO network and
NO API key — runners/preflights are stubbed via ``app.state``.

The consistent error envelope is ``{"error": {"type", "message", "detail"}}``
(see :mod:`agent_debate.api.errors`); every error path — request validation,
unknown ``run_id``, a missing API key, an unexpected fault — returns that shape
and never leaks a secret or a stack trace.
"""

from __future__ import annotations

import os

import pytest
from agent_debate.api.app import create_app
from agent_debate.api.config import (
    CORS_ORIGINS_ENV_VAR,
    DEFAULT_UI_ORIGIN,
    resolve_cors_origins,
)
from agent_debate.api.errors import ERROR_KEY
from agent_debate.api.preflight import set_preflight
from agent_debate.api.stream_runner import set_stream_runner
from agent_debate.core import DebateResult
from agent_debate.core.validation import MissingApiKeyError
from fastapi import FastAPI
from fastapi.testclient import TestClient

_TOPIC = "Should cities ban cars from downtown?"
_SECRET = "sk-super-secret-key-value"


def _stub_app() -> FastAPI:
    """Build an app whose streaming runner returns a canned result, no network."""
    app = create_app()

    def _runner(topic: str, overrides: dict[str, object], publish, run_id: str):  # type: ignore[no-untyped-def]
        return DebateResult(topic=topic)

    set_stream_runner(app, _runner)
    return app


def _error_body(response: object) -> dict[str, str]:
    """Return the ``error`` envelope from a JSON error response, asserting shape."""
    body = response.json()  # type: ignore[attr-defined]
    assert ERROR_KEY in body, body
    envelope: dict[str, str] = body[ERROR_KEY]
    assert set(envelope) == {"type", "message", "detail"}
    assert isinstance(envelope["type"], str) and envelope["type"]
    assert isinstance(envelope["message"], str) and envelope["message"]
    return envelope


def test_invalid_topic_returns_consistent_error_envelope() -> None:
    """An oversized topic is a 422 in the consistent ``error`` envelope."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": "x" * 5000})

    assert response.status_code == 422
    envelope = _error_body(response)
    assert "Topic" in str(envelope["detail"]) or "Topic" in envelope["message"]


def test_bad_override_returns_consistent_error_envelope() -> None:
    """A non-positive ``rounds`` override is rejected with the error envelope."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": _TOPIC, "rounds": 0})

    assert response.status_code == 422
    _error_body(response)


def test_unknown_extra_field_is_rejected() -> None:
    """An unknown body field is rejected (extra='forbid') with the envelope."""
    client = TestClient(_stub_app())

    response = client.post("/debates", json={"topic": _TOPIC, "bogus": 1})

    assert response.status_code == 422
    _error_body(response)


def test_unknown_run_id_returns_consistent_404() -> None:
    """An unknown ``run_id`` is a 404 in the consistent ``error`` envelope."""
    client = TestClient(_stub_app())

    response = client.get("/debates/does-not-exist")

    assert response.status_code == 404
    envelope = _error_body(response)
    assert "does-not-exist" in str(envelope["detail"]) or "does-not-exist" in envelope["message"]


def test_missing_api_key_returns_safe_503_without_leaking_key() -> None:
    """A preflight ``MissingApiKeyError`` is a 503 with a safe message, no key."""
    app = create_app()
    os.environ["_TEST_LEAK_PROBE"] = _SECRET

    def _boom() -> None:
        raise MissingApiKeyError(f"Missing required API key(s): {_SECRET}.")

    set_preflight(app, _boom)
    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/debates", json={"topic": _TOPIC}
        )
    finally:
        os.environ.pop("_TEST_LEAK_PROBE", None)

    assert response.status_code == 503
    envelope = _error_body(response)
    assert _SECRET not in response.text
    assert "key" in envelope["message"].lower()


def test_unexpected_error_returns_safe_500_without_stack_trace() -> None:
    """An unexpected fault is a 500 with a safe message and no stack trace."""
    app = create_app()

    def _boom() -> None:
        raise RuntimeError(f"internal boom {_SECRET}")

    set_preflight(app, _boom)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/debates", json={"topic": _TOPIC}
    )

    assert response.status_code == 500
    envelope = _error_body(response)
    assert _SECRET not in response.text
    assert "Traceback" not in response.text
    assert envelope["detail"] is None


def test_default_preflight_rejects_missing_key_via_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no injected runner and no key, the default preflight returns 503.

    This exercises the production path: ``default_preflight`` validates the
    active provider keys and the handler maps the resulting error to a safe 503.
    """
    from agent_debate.core import get_settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post("/debates", json={"topic": _TOPIC})

    assert response.status_code == 503
    envelope = _error_body(response)
    assert envelope["type"] == "server_misconfigured"


def test_invalid_input_handler_returns_422_envelope() -> None:
    """The :class:`InvalidInputError` safety-net handler yields a 422 envelope."""
    import asyncio

    from agent_debate.api.errors import _handle_invalid_input
    from agent_debate.core.security import InvalidInputError
    from starlette.requests import Request

    scope = {"type": "http", "path": "/debates", "headers": []}
    response = asyncio.run(
        _handle_invalid_input(Request(scope), InvalidInputError("Topic is bad."))
    )

    assert response.status_code == 422


def test_cors_allows_configured_ui_origin() -> None:
    """A request from the configured UI origin gets an allow-origin header."""
    client = TestClient(_stub_app())

    response = client.get("/health", headers={"Origin": DEFAULT_UI_ORIGIN})

    assert response.headers.get("access-control-allow-origin") == DEFAULT_UI_ORIGIN


def test_cors_preflight_allows_post_to_debates() -> None:
    """An OPTIONS preflight from the UI origin is allowed for POST /debates."""
    client = TestClient(_stub_app())

    response = client.options(
        "/debates",
        headers={
            "Origin": DEFAULT_UI_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") == DEFAULT_UI_ORIGIN


def test_cors_disallows_unconfigured_origin() -> None:
    """A request from a disallowed origin gets no allow-origin for that origin."""
    client = TestClient(_stub_app())

    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert response.headers.get("access-control-allow-origin") != "https://evil.example"


def test_cors_origin_is_config_driven(monkeypatch: pytest.MonkeyPatch) -> None:
    """Overriding the CORS env var changes the allowed origin (config-driven)."""
    custom = "https://debate.example.com"
    monkeypatch.setenv(CORS_ORIGINS_ENV_VAR, custom)

    assert resolve_cors_origins() == [custom]

    client = TestClient(_stub_app())
    response = client.get("/health", headers={"Origin": custom})
    assert response.headers.get("access-control-allow-origin") == custom


def test_resolve_cors_origins_defaults_to_ui_dev_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no env override the allowed origins default to the UI dev origin."""
    monkeypatch.delenv(CORS_ORIGINS_ENV_VAR, raising=False)

    assert resolve_cors_origins() == [DEFAULT_UI_ORIGIN]


def test_resolve_cors_origins_parses_comma_separated_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A comma-separated env value yields a trimmed list of origins."""
    monkeypatch.setenv(CORS_ORIGINS_ENV_VAR, "https://a.example, https://b.example")

    assert resolve_cors_origins() == ["https://a.example", "https://b.example"]
