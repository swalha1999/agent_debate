"""Unit tests for the rate-limit config loader (TASKS.md 13.1, issue #90).

Epic 13 is the API gatekeeper (``docs/prds/api-gatekeeper.md``): every external
LLM/search call passes through a single chokepoint that enforces *config-driven*
rate limits. Task 0.14 shipped the data file
(:mod:`tests.test_rate_limits_config` locks its shape); this task ships the
loader + Pydantic models that read it.

These tests prove the "0 hard-coded limits" guideline (§5.2): the loader reads
the real ``config/rate_limits.json`` *and* an explicit temp file with custom
values, so the numbers demonstrably come from the file rather than Python.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_debate.core.gatekeeper import (
    DEFAULT_SERVICE,
    RateLimitConfig,
    ServiceLimits,
    load_rate_limit_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RATE_LIMITS_PATH = REPO_ROOT / "config" / "rate_limits.json"


def test_loader_reads_real_config_version() -> None:
    """The default loader resolves the repo-root file and reads version 1.00."""
    config = load_rate_limit_config()
    assert isinstance(config, RateLimitConfig)
    assert config.version == "1.00"


def test_loader_exposes_required_services() -> None:
    """``default``/``anthropic``/``search`` all load as ``ServiceLimits``."""
    config = load_rate_limit_config()
    for name in ("default", "anthropic", "search"):
        assert isinstance(config.services[name], ServiceLimits)


def test_default_service_int_fields_match_file() -> None:
    """The ``default`` service's five int fields equal the file's values."""
    raw = json.loads(RATE_LIMITS_PATH.read_text(encoding="utf-8"))
    expected = raw["rate_limits"]["services"]["default"]
    limits = load_rate_limit_config().services["default"]
    assert limits.requests_per_minute == expected["requests_per_minute"]
    assert limits.requests_per_hour == expected["requests_per_hour"]
    assert limits.concurrent_max == expected["concurrent_max"]
    assert limits.retry_after_seconds == expected["retry_after_seconds"]
    assert limits.max_retries == expected["max_retries"]


def test_get_service_limits_returns_named_service() -> None:
    """``get_service_limits("anthropic")`` returns the anthropic limits."""
    config = load_rate_limit_config()
    raw = json.loads(RATE_LIMITS_PATH.read_text(encoding="utf-8"))
    expected = raw["rate_limits"]["services"]["anthropic"]
    limits = config.get_service_limits("anthropic")
    assert limits == config.services["anthropic"]
    assert limits.requests_per_minute == expected["requests_per_minute"]


def test_get_service_limits_falls_back_to_default() -> None:
    """An unconfigured service name falls back to the ``default`` service."""
    config = load_rate_limit_config()
    assert config.get_service_limits("unknown-service") is config.services[DEFAULT_SERVICE]


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    """A missing config path raises ``FileNotFoundError`` naming the path."""
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError, match=str(missing)):
        load_rate_limit_config(missing)


def test_malformed_file_raises_value_error(tmp_path: Path) -> None:
    """Invalid JSON raises a clear ``ValueError``."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="rate_limits.json"):
        load_rate_limit_config(bad)


def test_explicit_path_with_custom_values(tmp_path: Path) -> None:
    """Loading a custom file proves values come from the file, not code."""
    custom = tmp_path / "custom.json"
    payload = {
        "rate_limits": {
            "version": "9.99",
            "services": {
                "default": {
                    "requests_per_minute": 7,
                    "requests_per_hour": 11,
                    "concurrent_max": 1,
                    "retry_after_seconds": 13,
                    "max_retries": 0,
                }
            },
        }
    }
    custom.write_text(json.dumps(payload), encoding="utf-8")
    config = load_rate_limit_config(custom)
    assert config.version == "9.99"
    limits = config.get_service_limits("default")
    assert limits.requests_per_minute == 7
    assert limits.max_retries == 0


def test_service_limits_rejects_negative_rate(tmp_path: Path) -> None:
    """A non-positive ``requests_per_minute`` is rejected by validation."""
    custom = tmp_path / "neg.json"
    payload = {
        "rate_limits": {
            "version": "1.00",
            "services": {
                "default": {
                    "requests_per_minute": 0,
                    "requests_per_hour": 11,
                    "concurrent_max": 1,
                    "retry_after_seconds": 13,
                    "max_retries": 0,
                }
            },
        }
    }
    custom.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="rate_limits.json"):
        load_rate_limit_config(custom)
