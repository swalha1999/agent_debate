"""PRD §11 acceptance criteria — the SURFACES + HYGIENE/META half (issue #81).

Companion to ``test_acceptance_criteria.py`` (split to hold the 150-line cap, PRD
§3.2). This module maps the §11 bullets that are best verified by a meta-check or
by aggregating an existing scripted gate, rather than re-running a debate:

* §11.7  all five surfaces import (UI, CLI, API, SDK, LOG); every logged event
  carries a ``run_id`` → ``test_c7_*``
* §11.8  no secrets in the committed repo (``.env`` gitignored; the scanner
  catches a planted key) → ``test_c8_*``
* §11.10 coverage gate enforced at ``fail_under = 85`` → ``test_c10_*``
* §11.11 no code file exceeds 150 lines; config-driven (limit not hard-coded) →
  ``test_c11_*``
* §11.12 a version module starts at ``1.00``; the Prompt Book exists → ``test_c12_*``
* §11.13 dedicated sub-PRDs exist for all four mechanisms → ``test_c13_*``
* §11.14/§11.15 a completed run is reviewable evidence — transcript + verdict +
  token/cost totals saved to ``runs/<run_id>.jsonl`` (the form the notebook/teacher
  reads); the ``runs/`` dir is committed → ``test_c15_*``
"""

from __future__ import annotations

import importlib
import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
from _acceptance_criteria_helpers import REPO_ROOT, logged_events, rebutting_model, run_engine

_INITIAL_VERSION = "1.00"
_MAX_LINES = 150
_SURFACE_MODULES = (
    "agent_debate.core",
    "agent_debate.log",
    "agent_debate.api",
    "agent_debate.cli",
    "agent_debate.ui",
)
_SUB_PRDS = (
    "debate-orchestration.md",
    "anti-sycophancy.md",
    "api-gatekeeper.md",
    "search-plugin.md",
)


def _load_script(name: str) -> ModuleType:
    """Import a standalone ``scripts/<name>.py`` module by path (not a package)."""
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- §11.7 all five surfaces work; events carry run_id --------------------------


@pytest.mark.parametrize("module", _SURFACE_MODULES)
def test_c7_all_five_surfaces_import(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_c7_every_logged_event_carries_run_id(tmp_path: Path) -> None:
    run_engine(
        "c7",
        tmp_path,
        pro=rebutting_model("I rebut and counter that."),
        con=rebutting_model("I counter and rebut that."),
        rounds=2,
        max_words=50,
    )
    events = logged_events(tmp_path, "c7")
    assert events and all(e.get("run_id") == "c7" for e in events)


# --- §11.8 no secrets in repo (.env gitignored; scanner catches a planted key) --


def test_c8_secret_scanner_detects_a_planted_key_and_passes_clean(tmp_path: Path) -> None:
    scanner = _load_script("secret_scan")
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "ok.py").write_text("X = 'your-key-here'\n", encoding="utf-8")
    assert scanner.find_secrets(clean) == []  # placeholder is allowlisted, no hit
    planted = tmp_path / "planted"
    planted.mkdir()
    (planted / "leak.py").write_text(f"KEY = 'sk-{'A' * 40}'\n", encoding="utf-8")
    assert scanner.find_secrets(planted), "scanner must flag a planted key-like secret"


def test_c8_dotenv_is_gitignored_but_example_is_tracked() -> None:
    import subprocess

    ignored = subprocess.run(["git", "check-ignore", ".env"], cwd=REPO_ROOT, capture_output=True)
    assert ignored.returncode == 0, ".env must be gitignored"
    tracked = subprocess.run(
        ["git", "ls-files", ".env.example"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert ".env.example" in tracked.stdout


# --- §11.10 coverage gate enforced at >=85 --------------------------------------


def test_c10_coverage_gate_is_enforced_at_eighty_five() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["coverage"]["report"]["fail_under"] == 85


# --- §11.11 no file exceeds 150 lines; the limit is config-driven, not inline ---


def test_c11_no_code_file_exceeds_the_configured_line_limit() -> None:
    checker = _load_script("check_line_limit")
    assert checker.DEFAULT_MAX_LINES == _MAX_LINES  # single source of truth, not inline
    offenders = checker.find_offenders(REPO_ROOT, checker.DEFAULT_MAX_LINES)
    assert offenders == [], f"files over the {_MAX_LINES}-line guideline: {offenders}"


# --- §11.12 version module starts at 1.00; the Prompt Book is maintained --------


def test_c12_version_starts_at_one_zero_zero_and_prompt_book_exists() -> None:
    from agent_debate.core import __version__

    assert __version__ == _INITIAL_VERSION
    prompt_book = REPO_ROOT / "docs" / "PROMPTS.md"
    assert prompt_book.is_file() and prompt_book.read_text(encoding="utf-8").strip()


# --- §11.13 dedicated sub-PRDs exist for all four mechanisms ---------------------


@pytest.mark.parametrize("sub_prd", _SUB_PRDS)
def test_c13_dedicated_sub_prd_exists(sub_prd: str) -> None:
    path = REPO_ROOT / "docs" / "prds" / sub_prd
    assert path.is_file() and path.read_text(encoding="utf-8").strip()


# --- §11.14/§11.15 a completed run is reviewable evidence (transcript+verdict+cost)


def test_c15_completed_run_is_reviewable_evidence(tmp_path: Path) -> None:
    result = run_engine(
        "c15",
        tmp_path,
        pro=rebutting_model("However I rebut and counter that."),
        con=rebutting_model("On the contrary I counter that."),
        rounds=2,
        max_words=50,
    )
    # The saved run carries everything a reviewer/notebook needs (PRD §9/§10/§12.5).
    assert result.transcript and result.verdict is not None
    assert result.cost_breakdown is not None and result.totals.total_tokens >= 0
    assert (tmp_path / "c15" / "c15.jsonl").is_file()  # persisted as runs/<run_id>/<run_id>.jsonl
    assert (REPO_ROOT / "runs").is_dir()  # the runs/ dir is committed for review
