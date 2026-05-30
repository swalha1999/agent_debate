"""Rate-limit config models + loader for the API gatekeeper (task 13.1).

Epic 13 (``docs/prds/api-gatekeeper.md``) is the single chokepoint every
external LLM/search call passes through. This module is its *config* surface:
typed Pydantic models mirroring ``config/rate_limits.json`` and a loader that
reads them. Later tasks add ``ApiGatekeeper.execute`` (13.2), the FIFO overflow
queue (13.3), retry + concurrency (13.4) and ``get_queue_status`` (13.5).

"0 hard-coded limits" (sub-PRD §4 / guideline §5.2): no limit value (30, 500,
…) is baked into Python — every number is read from the file. The only literals
here are the config file *name* (one named constant) and the fallback service
*key* ``"default"`` — both identifiers, not limit values.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.log import get_logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_LOG = get_logger("gatekeeper.config")

#: Repo-root-relative location of the versioned rate-limit data file (task 0.14).
#: The *path* is the one acceptable constant — it names the file, not a limit.
RATE_LIMITS_FILENAME = "rate_limits.json"
_CONFIG_DIRNAME = "config"

#: Service key used when a requested service has no explicit entry (sub-PRD §4
#: defines a ``default`` service for exactly this fallback). A key name, not a
#: limit value.
DEFAULT_SERVICE = "default"

#: This file lives at ``packages/core/src/agent_debate/core/gatekeeper/`` —
#: six parents up is the repo root, so the data file resolves regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[6]


class ServiceLimits(BaseModel):
    """Per-service rate limits — every value comes from the config file.

    All fields are required (no default *values*, so nothing bakes the numbers
    into code). Throughput fields must be positive; ``max_retries`` may be ``0``
    (no retries) so it is only required non-negative. ``queue_max_depth`` bounds
    the FIFO overflow queue (task 13.3) and must be positive (a zero-depth queue
    could never absorb overflow).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    requests_per_minute: int = Field(gt=0)
    requests_per_hour: int = Field(gt=0)
    concurrent_max: int = Field(gt=0)
    retry_after_seconds: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    queue_max_depth: int = Field(gt=0)


class RateLimitConfig(BaseModel):
    """Parsed view of ``config/rate_limits.json`` (the ``rate_limits`` body).

    Mirrors the file shape minus the top-level ``rate_limits`` wrapper, which
    :func:`load_rate_limit_config` unwraps before validation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    services: dict[str, ServiceLimits]

    def get_service_limits(self, name: str) -> ServiceLimits:
        """Return ``name``'s limits, falling back to the ``default`` service.

        Per the sub-PRD's ``default`` service intent: services without an
        explicit entry inherit the default limits rather than failing.
        """
        return self.services.get(name, self.services[DEFAULT_SERVICE])


def _default_path() -> Path:
    """Resolve ``config/rate_limits.json`` at the repo root (cwd-independent)."""
    return _REPO_ROOT / _CONFIG_DIRNAME / RATE_LIMITS_FILENAME


def load_rate_limit_config(path: Path | None = None) -> RateLimitConfig:
    """Load, parse and validate the rate-limit config from ``path``.

    :param path: explicit JSON file; defaults to the repo-root
        ``config/rate_limits.json`` resolved robustly (not from cwd).
    :raises FileNotFoundError: if the file does not exist (message names it).
    :raises ValueError: if the JSON is malformed or fails schema validation.
    """
    config_path = path if path is not None else _default_path()
    if not config_path.is_file():
        raise FileNotFoundError(f"rate_limits.json not found: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = RateLimitConfig.model_validate(raw["rate_limits"])
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        raise ValueError(f"invalid rate_limits.json at {config_path}: {exc}") from exc
    _LOG.debug(
        "rate_limit_config_loaded",
        version=config.version,
        services=sorted(config.services),
        path=str(config_path),
    )
    return config


__all__ = [
    "DEFAULT_SERVICE",
    "RATE_LIMITS_FILENAME",
    "RateLimitConfig",
    "ServiceLimits",
    "load_rate_limit_config",
]
