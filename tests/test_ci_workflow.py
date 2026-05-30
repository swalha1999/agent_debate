"""CI quality-gate workflow contract tests (TASKS.md 0.8, issue #8).

Task 0.8 establishes the CI quality gates *early* (PRD §6/§7, §9): on every
push and pull request the pipeline runs the full gate stack and fails the build
if any gate fails. These tests lock that contract so a later edit cannot
silently drop a gate or reorder the pipeline so a cheap check stops guarding an
expensive one.

The required gates, in pipeline order:

#. ``uv sync`` — install the workspace into the shared venv;
#. ``ruff check .`` — 0-violation lint gate (PRD §7.1);
#. ``ruff format --check .`` — formatting gate;
#. ``mypy`` — strict-ish type gate;
#. ``pytest --cov`` — tests + ≥85% coverage; the threshold is config-driven via
   ``[tool.coverage.report].fail_under`` in ``pyproject.toml`` (task 0.9), so CI
   carries no hard-coded number that could diverge from config (§6.2);
#. a 150-line-per-file check (script lands in task 0.10);
#. a secret scan (lands in task 0.11).

The line-limit and secret-scan steps are wired *forward-compatibly*: they
no-op cleanly (skip-if-absent + an echo) until 0.10/0.11 drop in their tooling,
so the scaffold pipeline is GREEN today and the gate activates automatically
later. The test asserts those steps are *present and reference their tooling*
without requiring the tooling to exist yet.

pyyaml is not a workspace dependency, so the workflow is validated with robust
substring/order assertions over the raw text rather than a YAML parse.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: Gate command fragments that must appear, in this exact pipeline order. The
#: coverage step is config-driven: ``pytest --cov`` enforces the ≥85% threshold
#: from ``[tool.coverage.report].fail_under`` in pyproject (task 0.9), so no
#: hard-coded ``--cov-fail-under`` number lives in the workflow.
ORDERED_GATE_FRAGMENTS = (
    "uv sync",
    "ruff check .",
    "ruff format --check .",
    "mypy",
    "pytest --cov",
    "check_line_limit.py",
    "secret",
)


def _workflow_text() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def test_ci_workflow_file_exists() -> None:
    """The CI workflow lives at the conventional Actions path."""
    assert CI_WORKFLOW.is_file(), f"missing CI workflow: {CI_WORKFLOW}"


def test_ci_triggers_on_push_and_pull_request() -> None:
    """The pipeline runs on both push and pull_request events."""
    text = _workflow_text()
    assert "push:" in text
    assert "pull_request:" in text


def test_ci_uses_official_setup_uv_action() -> None:
    """uv is provisioned via the official astral-sh/setup-uv action."""
    assert "astral-sh/setup-uv" in _workflow_text()


def test_ci_pins_python_312() -> None:
    """CI pins Python 3.12 to match .python-version."""
    assert "3.12" in _workflow_text()


def test_ci_runs_all_gates_in_order() -> None:
    """Every required gate is present and appears in pipeline order."""
    text = _workflow_text()
    last_index = -1
    for fragment in ORDERED_GATE_FRAGMENTS:
        index = text.find(fragment)
        assert index != -1, f"CI workflow is missing gate fragment: {fragment!r}"
        assert index > last_index, f"gate out of order: {fragment!r}"
        last_index = index


def test_line_limit_step_is_forward_compatible() -> None:
    """The 150-line check skips cleanly until task 0.10 lands the script."""
    text = _workflow_text()
    assert "scripts/check_line_limit.py" in text
    # Guarded by an existence check so the scaffold stays green pre-0.10.
    assert "if [ -f scripts/check_line_limit.py ]" in text


def test_secret_scan_step_is_forward_compatible() -> None:
    """The secret scan skips cleanly until task 0.11 lands the tooling."""
    text = _workflow_text().lower()
    assert "secret" in text
    # Forward-compatible: a skip-if-absent guard keeps the scaffold green.
    assert "pending task 0.11" in text
