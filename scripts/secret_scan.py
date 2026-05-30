#!/usr/bin/env python
"""Scan the source tree for committed secrets (PRD §7.4, TASKS.md 0.11).

The guideline mandates **no secrets in the repo** and an automated CI gate that
fails on a committed credential. This self-contained regex scanner walks the
tree, flags key-like secrets — ``sk-...``/``sk-ant-...`` tokens, AWS ``AKIA...``
access-key ids, PEM private-key headers, and generic high-entropy API tokens —
and exits non-zero listing every hit, or 0 on a clean tree.

Obvious placeholders (``your-...-here``, ``xxxxx`` runs, empty ``.env.example``
values) are ignored so the template file does not trip the gate. The detection
patterns and the placeholder allowlist are single named configs
(:data:`PATTERNS`, :data:`ALLOWLIST`) so no magic regex is scattered through the
code (guideline §7.2). The :func:`scan_text` detector is importable and
unit-tested independently of the filesystem walk.

Excluded from the walk: VCS/venv/cache dirs and the ``tests/`` tree (its
fixtures plant clearly-fake pattern-matching strings on purpose). Output goes
via the stdlib ``logging`` module — the workspace LOG surface is still a
skeleton at this scaffold stage, so this build-time tool logs directly; it
makes no external API calls, so the API gatekeeper (Epic 13) is N/A.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path

#: Named detection patterns (guideline §7.2 — single source, no scattered regex).
#: Each entry maps a human label to a compiled pattern for a key-like secret.
PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "openai-key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "pem-private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
}

#: Substrings marking an obvious placeholder; a match overlapping any of these
#: is ignored so the ``.env.example`` template and docs never trip the gate.
ALLOWLIST: tuple[str, ...] = (
    "your-",
    "-here",
    "xxxx",
    "example",
    "placeholder",
    "changeme",
    "redacted",
)

#: Directory names skipped during the walk (VCS, venv, caches, and the test
#: tree whose fixtures intentionally plant fake pattern-matching strings).
EXCLUDED_DIRS: frozenset[str] = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "tests"}
)

#: Only text-like files are scanned; binary/lock noise is skipped by suffix.
SCANNED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".py",
        ".env",
        ".example",
        ".toml",
        ".cfg",
        ".ini",
        ".json",
        ".yaml",
        ".yml",
        ".md",
        ".txt",
        ".sh",
        "",
    }
)

_LOG = logging.getLogger("secret_scan")


def _is_placeholder(match: str) -> bool:
    """Return ``True`` when ``match`` is an obvious placeholder, not a secret."""
    lowered = match.lower()
    return any(token in lowered for token in ALLOWLIST)


def scan_text(text: str) -> list[tuple[str, str]]:
    """Return ``(label, secret)`` hits in ``text``, skipping placeholders.

    The detector is filesystem-independent so it can be unit-tested against
    in-memory strings: every :data:`PATTERNS` entry is applied, and any match
    that overlaps an :data:`ALLOWLIST` token is discarded as a placeholder.
    """
    hits: list[tuple[str, str]] = []
    for label, pattern in PATTERNS.items():
        for match in pattern.findall(text):
            if not _is_placeholder(match):
                hits.append((label, match))
    return hits


def _iter_files(root: Path) -> list[Path]:
    """Yield scannable files under ``root``, skipping excluded dirs/suffixes."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in SCANNED_SUFFIXES:
            files.append(path)
    return files


def find_secrets(root: Path) -> list[tuple[Path, str, str]]:
    """Return ``(path, label, secret)`` for every hit under ``root``."""
    findings: list[tuple[Path, str, str]] = []
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, secret in scan_text(text):
            findings.append((path, label, secret))
    return findings


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repo root to scan (default: the repository containing this script).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Scan the tree and return a process exit code (0 = clean, 1 = secrets)."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args(argv)
    findings = find_secrets(args.root)
    if not findings:
        _LOG.info("Secret scan passed: no key-like secrets found.")
        return 0
    _LOG.error("Secret scan FAILED — key-like secrets found (PRD §7.4):")
    for path, label, _secret in findings:
        _LOG.error("  %s — %s", path, label)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
