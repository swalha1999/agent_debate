"""Config-driven FIFO log-file rotation for the JSONL sink (issue #217, §8.6).

HW2 ``docs/hw2_requirements.pdf`` §8.6 requires built-in logs to use **FIFO file
rotation**: a capped number of files, each with a maximum line count, with the
*oldest* file dropped first once the cap is exceeded. This module adds exactly
that to the per-run JSONL sink without disturbing its public path.

Rotation scheme (logrotate-style, deterministic)::

    <run_id>.jsonl     <- the live/current file (always this path: backward compat)
    <run_id>.1.jsonl   <- most-recently archived segment
    <run_id>.2.jsonl   <- older
    ...                   higher index == older

When the live file reaches ``max_lines_per_file`` lines, it rolls over: every
archive index shifts up by one (``.1`` -> ``.2`` ...), the live file becomes
``.1``, and a fresh empty live file is opened. To honour the ``max_files`` cap
(live + archives), the OLDEST archive — the highest surviving index — is deleted
first (FIFO) before the shift. The live, unsuffixed file therefore always holds
the newest events, so every existing reader of ``runs/<run_id>.jsonl`` keeps
working.

"0 hard-coded limits" (guideline §7.2): every count comes from
``config/logging.json`` (mirroring ``config/rate_limits.json`` /
``config/watchdog.json``) via :func:`load_rotation_config`, with the PDF example
(20 files x 500 lines) as the named ``DEFAULT_*`` fallback — no count is baked
into the writer.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TextIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError

#: PDF §8.6 example caps — the single source of truth for the shipped defaults.
DEFAULT_MAX_FILES = 20
DEFAULT_MAX_LINES_PER_FILE = 500

#: Repo-root-relative location of the versioned logging config. The *path* names
#: the file; it is not a limit value, so it is an acceptable named constant.
LOGGING_FILENAME = "logging.json"
_CONFIG_DIRNAME = "config"

#: This module lives at ``packages/log/src/agent_debate/log/`` — five parents up
#: is the repo root, so the data file resolves regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[5]


class RotationConfig(BaseModel):
    """FIFO rotation knobs — every value comes from config, none baked in code."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    max_files: int = Field(gt=0)
    max_lines_per_file: int = Field(gt=0)


def _default_path() -> Path:
    """Resolve ``config/logging.json`` at the repo root (cwd-independent)."""
    return _REPO_ROOT / _CONFIG_DIRNAME / LOGGING_FILENAME


def load_rotation_config(path: Path | None = None) -> RotationConfig:
    """Load, parse and validate the rotation config from ``path``.

    :param path: explicit JSON file; defaults to the repo-root
        ``config/logging.json`` resolved robustly (not from cwd).
    :raises ValueError: if the file is missing, malformed or fails validation.
    """
    config_path = path if path is not None else _default_path()
    if not config_path.is_file():
        raise ValueError(f"logging.json not found: {config_path}")
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        return RotationConfig.model_validate(raw["logging"])
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        raise ValueError(f"invalid logging.json at {config_path}: {exc}") from exc


def _archive_path(base: Path, index: int) -> Path:
    """Return the archive path for ``base`` at 1-based ``index`` (``<stem>.N``)."""
    return base.with_name(f"{base.stem}.{index}{base.suffix}")


class RotatingJsonlSink:
    """A line-counting JSONL sink that rotates files FIFO within configured caps.

    Behaves like a write-only text handle (``write``/``flush``/``close``) so it
    is a drop-in for the per-run sink. The live file is always ``base`` itself;
    archives use the ``<stem>.N<suffix>`` scheme documented at module level.
    """

    def __init__(self, base: Path, config: RotationConfig) -> None:
        self._base = base
        self._config = config
        self._line_count = self._count_existing_lines(base)
        self._handle: TextIO = base.open("a", encoding="utf-8")

    @staticmethod
    def _count_existing_lines(path: Path) -> int:
        """Return the number of non-blank lines already in ``path`` (0 if new)."""
        if not path.is_file():
            return 0
        text = path.read_text(encoding="utf-8")
        return sum(1 for line in text.splitlines() if line.strip())

    def write(self, line: str) -> None:
        """Write one event ``line`` (newline-terminated), rotating when full."""
        if self._line_count >= self._config.max_lines_per_file:
            self._rotate()
        self._handle.write(line)
        self._handle.flush()
        self._line_count += 1

    def _rotate(self) -> None:
        """Close the full live file, shift archives up, drop the oldest (FIFO)."""
        self._handle.close()
        self._evict_and_shift()
        self._base.replace(_archive_path(self._base, 1))
        self._handle = self._base.open("a", encoding="utf-8")
        self._line_count = 0

    def _evict_and_shift(self) -> None:
        """Delete the oldest archive past the cap, then shift each archive up."""
        # Existing archives, newest (index 1) first. ``max_files`` counts the
        # live file too, so at most ``max_files - 1`` archives may survive.
        existing = sorted(self._existing_archive_indices())
        keep = self._config.max_files - 1
        for index in existing:
            if index >= keep:  # this archive would overflow the cap -> FIFO drop
                _archive_path(self._base, index).unlink(missing_ok=True)
        for index in sorted((i for i in existing if i < keep), reverse=True):
            _archive_path(self._base, index).replace(_archive_path(self._base, index + 1))

    def _existing_archive_indices(self) -> list[int]:
        """Return the indices of archive files currently on disk for this base."""
        stem, suffix = re.escape(self._base.stem), re.escape(self._base.suffix)
        pattern = re.compile(rf"^{stem}\.(\d+){suffix}$")
        indices: list[int] = []
        for path in self._base.parent.glob(f"{self._base.stem}.*{self._base.suffix}"):
            match = pattern.match(path.name)
            if match is not None:
                indices.append(int(match.group(1)))
        return indices

    def flush(self) -> None:
        """Flush the live file handle."""
        self._handle.flush()

    def close(self) -> None:
        """Close the live file handle."""
        if not self._handle.closed:
            self._handle.close()

    @property
    def closed(self) -> bool:
        """Whether the live file handle is closed (mirrors :class:`TextIO`)."""
        return self._handle.closed


__all__ = [
    "DEFAULT_MAX_FILES",
    "DEFAULT_MAX_LINES_PER_FILE",
    "LOGGING_FILENAME",
    "RotatingJsonlSink",
    "RotationConfig",
    "load_rotation_config",
]
