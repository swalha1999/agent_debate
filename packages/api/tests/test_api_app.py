"""Tests for the FastAPI app factory + health endpoint (task 10.1, issue #68).

TDD: these assert the skeleton contract before the code exists. The debate
endpoints (10.2), SSE (10.3) and CORS/validation (10.4) are out of scope here —
we only prove the app factory, the health route and the config-driven Uvicorn
entrypoint, all without binding a real port or making any network call.
"""

from __future__ import annotations

from agent_debate.api.app import create_app
from agent_debate.core import __version__
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_create_app_returns_fastapi_instance() -> None:
    """``create_app()`` returns a configured :class:`FastAPI` instance."""
    app = create_app()

    assert isinstance(app, FastAPI)


def test_app_factory_is_reusable() -> None:
    """Two calls yield two independent app instances (factory pattern)."""
    first = create_app()
    second = create_app()

    assert first is not second


def test_health_endpoint_returns_ok_and_version() -> None:
    """``GET /health`` returns 200 with status ``ok`` and the SDK version."""
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_root_endpoint_returns_service_info() -> None:
    """``GET /`` returns service info including the version."""
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert "service" in body


def test_app_is_importable_and_constructed_at_module_level() -> None:
    """The module-level ``app`` (used by uvicorn) is a built FastAPI instance."""
    from agent_debate.api.app import app

    assert isinstance(app, FastAPI)
