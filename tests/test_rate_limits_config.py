"""Contract tests for ``config/rate_limits.json`` (TASKS.md 0.14, issue #14).

This is the single source of truth for the API gatekeeper's rate limits
(``docs/prds/api-gatekeeper.md`` §4): the loader ``RateLimitConfig`` lands in
Epic 13, so this task ships only the *file*. These assertions lock its shape so
Epic 13 — and the "0 hard-coded limits" guideline (§5.2) — can rely on it:

* the file exists at the repo root under ``config/`` and parses as JSON;
* ``rate_limits.version`` is the string ``"1.00"``;
* services ``default``/``anthropic``/``search`` each carry the five required
  integer keys with the exact values mandated by the sub-PRD.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RATE_LIMITS_PATH = REPO_ROOT / "config" / "rate_limits.json"

REQUIRED_SERVICES = ("default", "anthropic", "search")
REQUIRED_KEYS = (
    "requests_per_minute",
    "requests_per_hour",
    "concurrent_max",
    "retry_after_seconds",
    "max_retries",
)

# Exact shape mandated by docs/prds/api-gatekeeper.md §4 — the file must match.
EXPECTED_SERVICES = {
    "default": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3,
    },
    "anthropic": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "concurrent_max": 5,
        "retry_after_seconds": 30,
        "max_retries": 3,
    },
    "search": {
        "requests_per_minute": 20,
        "requests_per_hour": 300,
        "concurrent_max": 3,
        "retry_after_seconds": 15,
        "max_retries": 2,
    },
}


def _load() -> dict[str, object]:
    with RATE_LIMITS_PATH.open(encoding="utf-8") as handle:
        data: dict[str, object] = json.load(handle)
    return data


def test_config_file_exists() -> None:
    """``config/rate_limits.json`` is present at the repo root."""
    assert RATE_LIMITS_PATH.is_file()


def test_config_parses_as_json() -> None:
    """The file is valid JSON with a top-level ``rate_limits`` object."""
    data = _load()
    assert isinstance(data["rate_limits"], dict)


def test_version_is_one_dot_zero_zero() -> None:
    """``rate_limits.version`` is the string ``"1.00"``."""
    rate_limits = _load()["rate_limits"]
    assert isinstance(rate_limits, dict)
    assert rate_limits["version"] == "1.00"


def _services() -> dict[str, dict[str, object]]:
    rate_limits = _load()["rate_limits"]
    assert isinstance(rate_limits, dict)
    services = rate_limits["services"]
    assert isinstance(services, dict)
    return services


def test_required_services_present() -> None:
    """``default``/``anthropic``/``search`` are all defined."""
    assert set(_services()) >= set(REQUIRED_SERVICES)


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_has_required_integer_keys(service: str) -> None:
    """Each service carries the five required keys, all integers."""
    entry = _services()[service]
    assert isinstance(entry, dict)
    for key in REQUIRED_KEYS:
        assert isinstance(entry[key], int)
        # JSON booleans are ints in Python; rate limits must be real integers.
        assert not isinstance(entry[key], bool)


@pytest.mark.parametrize("service", REQUIRED_SERVICES)
def test_service_values_match_sub_prd(service: str) -> None:
    """Values match docs/prds/api-gatekeeper.md §4 exactly."""
    assert _services()[service] == EXPECTED_SERVICES[service]
