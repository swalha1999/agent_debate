"""Tests for the in-repo secret scanner (TASKS.md 0.11, issue #11).

The guideline (PRD §7.4, "no secrets in the repo") mandates a CI gate that
fails on a committed credential. ``scripts/secret_scan.py`` walks the source
tree, detects key-like secrets (``sk-...``/``sk-ant-...`` tokens, AWS
``AKIA...`` access keys, PEM private-key headers, generic high-entropy API
tokens), ignores obvious placeholders (``your-...-here``, ``xxxxx``, empty
values), and exits non-zero listing every hit.

These tests are written first (TDD red→green, §6.1). They exercise the
importable detection helper and the ``main()`` entry point against in-memory
strings and synthetic trees, so the suite never commits a real secret, and
assert the live tree passes the scan. The single planted "secret" below is a
clearly fake but pattern-matching literal kept only in this test file; the
real-tree walk excludes ``tests/`` so the live scan still passes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "secret_scan.py"

# Clearly fake, in-test-only literals that still match the detection patterns.
FAKE_OPENAI = "sk-" + "A" * 40
FAKE_ANTHROPIC = "sk-ant-" + "B" * 95
FAKE_AWS = "AKIA" + "Q" * 16
FAKE_PEM = "-----BEGIN RSA PRIVATE KEY-----"


def _load_module() -> ModuleType:
    """Import the standalone script by path (``scripts/`` is not a package)."""
    spec = importlib.util.spec_from_file_location("secret_scan", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_file_exists() -> None:
    """The scanner lives at the path CI's forward-compatible guard expects."""
    assert SCRIPT_PATH.is_file(), f"missing script: {SCRIPT_PATH}"


def test_scan_text_flags_openai_key() -> None:
    """An ``sk-...`` token is detected."""
    mod = _load_module()
    hits = mod.scan_text(f"OPENAI_KEY = {FAKE_OPENAI!r}")
    assert hits, "expected the sk- token to be flagged"


def test_scan_text_flags_anthropic_key() -> None:
    """An ``sk-ant-...`` token is detected."""
    mod = _load_module()
    assert mod.scan_text(f"key={FAKE_ANTHROPIC}")


def test_scan_text_flags_aws_access_key() -> None:
    """An AWS ``AKIA...`` access-key id is detected."""
    mod = _load_module()
    assert mod.scan_text(f"aws = {FAKE_AWS}")


def test_scan_text_flags_pem_private_key_header() -> None:
    """A PEM private-key header is detected."""
    mod = _load_module()
    assert mod.scan_text(FAKE_PEM)


def test_scan_text_ignores_your_x_here_placeholder() -> None:
    """A ``your-...-here`` placeholder is not a hit."""
    mod = _load_module()
    assert not mod.scan_text("ANTHROPIC_API_KEY=your-anthropic-api-key-here")


def test_scan_text_ignores_xxxxx_placeholder() -> None:
    """An obvious ``xxxxx`` placeholder is not a hit."""
    mod = _load_module()
    assert not mod.scan_text("token = sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")


def test_scan_text_ignores_empty_assignment() -> None:
    """An empty value (as in ``.env.example``) is not a hit."""
    mod = _load_module()
    assert not mod.scan_text("SEARCH_API_KEY=")


def test_scan_text_clean_string_has_no_hits() -> None:
    """Ordinary prose/code yields no hits."""
    mod = _load_module()
    assert not mod.scan_text("def add(a: int, b: int) -> int:\n    return a + b\n")


def test_main_passes_on_clean_tree(tmp_path: Path) -> None:
    """A tree with no secrets exits 0."""
    mod = _load_module()
    pkg = tmp_path / "packages" / "demo" / "src"
    pkg.mkdir(parents=True)
    (pkg / "ok.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_main_reports_and_fails_on_planted_secret(tmp_path: Path, caplog: object) -> None:
    """A planted key-like secret is listed and forces a non-zero exit."""
    import logging

    mod = _load_module()
    pkg = tmp_path / "packages" / "demo" / "src"
    pkg.mkdir(parents=True)
    leak = pkg / "leak.py"
    leak.write_text(f'KEY = "{FAKE_AWS}"\n', encoding="utf-8")
    with caplog.at_level(logging.ERROR):  # type: ignore[attr-defined]
        exit_code = mod.main(["--root", str(tmp_path)])
    assert exit_code == 1
    assert "leak.py" in caplog.text  # type: ignore[attr-defined]


def test_main_excludes_git_and_venv(tmp_path: Path) -> None:
    """Hits inside excluded dirs (.git/.venv) do not fail the scan."""
    mod = _load_module()
    for excluded in (".git", ".venv"):
        d = tmp_path / excluded
        d.mkdir()
        (d / "noise.txt").write_text(f"{FAKE_AWS}\n", encoding="utf-8")
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_patterns_and_allowlist_are_named_config() -> None:
    """Detection is driven by a single named PATTERNS/ALLOWLIST config."""
    mod = _load_module()
    assert mod.PATTERNS, "PATTERNS config must be defined"
    assert mod.ALLOWLIST, "ALLOWLIST config must be defined"


def test_live_tree_passes_scan() -> None:
    """The committed repo carries no secrets, so the gate exits 0."""
    mod = _load_module()
    assert mod.main([]) == 0
