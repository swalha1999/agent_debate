"""Tests for the 150-line-per-file check (TASKS.md 0.10, issue #10).

The guideline (PRD §3.2) caps every code file at 150 lines and mandates the
limit be enforced by an automated CI check. ``scripts/check_line_limit.py``
walks ``packages/**/*.py``, counts *code* lines — excluding blank lines,
comment-only lines and triple-quoted docstring/string bodies — and exits
non-zero listing any file over the threshold.

These tests are written first (TDD red→green, §6.1). They exercise the
importable counting helper and the ``main()`` entry point against synthetic
trees so the suite never depends on the real package line counts, and assert
the live scaffold passes the check.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_line_limit.py"


def _load_module() -> ModuleType:
    """Import the standalone script by path (``scripts/`` is not a package)."""
    spec = importlib.util.spec_from_file_location("check_line_limit", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_file_exists() -> None:
    """The check script lives at the path CI's forward-compatible guard expects."""
    assert SCRIPT_PATH.is_file(), f"missing script: {SCRIPT_PATH}"


def test_count_code_lines_excludes_blanks_and_comments(tmp_path: Path) -> None:
    """Blank lines and comment-only lines do not count as code."""
    mod = _load_module()
    src = tmp_path / "sample.py"
    src.write_text(
        "\n".join(
            [
                "# a comment-only line",
                "",
                "   ",  # whitespace-only
                "x = 1  # trailing comment counts as code",
                "    # indented comment",
                "y = 2",
            ]
        ),
        encoding="utf-8",
    )
    assert mod.count_code_lines(src) == 2


def test_count_code_lines_excludes_docstring_bodies(tmp_path: Path) -> None:
    """Triple-quoted docstring/string lines are not counted as code."""
    mod = _load_module()
    src = tmp_path / "doc.py"
    src.write_text(
        '"""Module docstring.\n\nSpanning several\nlines of prose.\n"""\n\nz = 3\n',
        encoding="utf-8",
    )
    assert mod.count_code_lines(src) == 1


def test_main_passes_on_clean_tree(tmp_path: Path) -> None:
    """A tree whose files are all under the threshold exits 0."""
    mod = _load_module()
    pkg = tmp_path / "packages" / "demo" / "src"
    pkg.mkdir(parents=True)
    (pkg / "ok.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_main_reports_and_fails_over_threshold(tmp_path: Path, caplog: object) -> None:
    """A file over the threshold is listed and forces a non-zero exit."""
    import logging

    mod = _load_module()
    pkg = tmp_path / "packages" / "demo" / "src"
    pkg.mkdir(parents=True)
    big = pkg / "too_big.py"
    big.write_text("\n".join(f"v{i} = {i}" for i in range(200)) + "\n", encoding="utf-8")
    with caplog.at_level(logging.ERROR):  # type: ignore[attr-defined]
        exit_code = mod.main(["--root", str(tmp_path), "--max-lines", "150"])
    assert exit_code == 1
    assert "too_big.py" in caplog.text  # type: ignore[attr-defined]


def test_threshold_override_can_fail_small_files(tmp_path: Path) -> None:
    """The --max-lines override is honoured (no hard-coded magic threshold)."""
    mod = _load_module()
    pkg = tmp_path / "packages" / "demo" / "src"
    pkg.mkdir(parents=True)
    (pkg / "five.py").write_text("a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n", encoding="utf-8")
    assert mod.main(["--root", str(tmp_path), "--max-lines", "3"]) == 1


def test_default_max_lines_constant_is_150() -> None:
    """The single named default threshold matches the guideline (§3.2)."""
    mod = _load_module()
    assert mod.DEFAULT_MAX_LINES == 150


def test_live_scaffold_passes_check() -> None:
    """The current packages/ tree is under the limit, so the gate exits 0."""
    mod = _load_module()
    assert mod.main([]) == 0
