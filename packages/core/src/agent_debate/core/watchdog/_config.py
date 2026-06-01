"""Config model + loader for the keep-alive Watchdog (issue #216, HW2 §8.6).

HW2 §8.6 — *Watchdog with keep-alive*: a fallen worker must be detected and
restarted. Its knobs (heartbeat interval, liveness timeout, max restarts) are
config-driven, NOT hard-coded — mirroring the rate-limit config surface
(:mod:`agent_debate.core.gatekeeper.config`): a typed Pydantic model plus a
loader that reads ``config/watchdog.json`` from the repo root (cwd-independent).

"0 hard-coded limits" (guideline §7.2): no interval/timeout/restart *value* is
baked into Python — every number is read from the file. The only literals here
are the config file *name* (one named constant) and the ``config`` dir name —
both identifiers, not limit values.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_debate.log import get_logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

_LOG = get_logger("watchdog.config")

#: Repo-root-relative location of the versioned watchdog data file. The *path* is
#: the one acceptable constant — it names the file, not a limit value.
WATCHDOG_FILENAME = "watchdog.json"
_CONFIG_DIRNAME = "config"

#: This file lives at ``packages/core/src/agent_debate/core/watchdog/`` — six
#: parents up is the repo root, so the data file resolves regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[6]


class WatchdogConfig(BaseModel):
    """Keep-alive Watchdog knobs — every value comes from the config file.

    All fields are required (no default *values*, so nothing bakes a number into
    code). The two durations must be positive (a zero interval/timeout could
    never detect a fall sanely); ``max_restarts`` may be ``0`` (give up on the
    first fall) so it is only required non-negative.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    heartbeat_interval_s: float = Field(gt=0)
    liveness_timeout_s: float = Field(gt=0)
    max_restarts: int = Field(ge=0)


def _default_path() -> Path:
    """Resolve ``config/watchdog.json`` at the repo root (cwd-independent)."""
    return _REPO_ROOT / _CONFIG_DIRNAME / WATCHDOG_FILENAME


def load_watchdog_config(path: Path | None = None) -> WatchdogConfig:
    """Load, parse and validate the watchdog config from ``path``.

    :param path: explicit JSON file; defaults to the repo-root
        ``config/watchdog.json`` resolved robustly (not from cwd).
    :raises FileNotFoundError: if the file does not exist (message names it).
    :raises ValueError: if the JSON is malformed or fails schema validation.
    """
    config_path = path if path is not None else _default_path()
    if not config_path.is_file():
        raise FileNotFoundError(f"watchdog.json not found: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        config = WatchdogConfig.model_validate(raw["watchdog"])
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        raise ValueError(f"invalid watchdog.json at {config_path}: {exc}") from exc
    _LOG.debug(
        "watchdog_config_loaded",
        version=config.version,
        liveness_timeout_s=config.liveness_timeout_s,
        max_restarts=config.max_restarts,
        path=str(config_path),
    )
    return config


__all__ = ["WATCHDOG_FILENAME", "WatchdogConfig", "load_watchdog_config"]
