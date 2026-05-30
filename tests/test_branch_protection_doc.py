"""Contract tests for the branch-protection rule (TASKS.md 0.15, issue #15).

The ``main`` branch is protected so the CI **Quality gates** check must pass
before a pull request can merge. Branch protection itself lives in GitHub's
settings (applied via ``gh api``) and cannot be asserted from CI without an
authenticated token, so these tests lock the *documentation + reproducibility
contract* instead:

* the README documents that ``main`` is protected, that the CI check is
  required, and that direct pushes are disallowed;
* a re-apply script (``scripts/setup_branch_protection.sh``) exists, is
  executable, and references the exact required-check name so the protection
  can be reproduced from version control rather than clicked through a UI.

This is the testable surface of the task: the live ``gh api`` call is a one-off
admin action, but the contract that the rule is *documented and reproducible*
is what we guard here.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup_branch_protection.sh"

#: The exact GitHub check-run name produced by the ``quality-gates`` job in
#: ``.github/workflows/ci.yml`` (its ``name:`` field). The protection rule and
#: every reference to it must use this single string.
REQUIRED_CHECK_NAME = "Quality gates"


def _readme_text() -> str:
    return README.read_text(encoding="utf-8")


def _has_heading(text: str, *alternatives: str) -> bool:
    """True if a Markdown heading matches any alternative (case-insensitive)."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip().lower()
        if any(re.search(alt.lower(), title) for alt in alternatives):
            return True
    return False


def test_readme_documents_branch_protection() -> None:
    """The README explains that ``main`` is protected and how merges are gated."""
    text = _readme_text()
    lowered = text.lower()
    assert _has_heading(text, "branch protection", "protected")
    assert "branch protection" in lowered or "protected" in lowered
    assert "main" in lowered


def test_readme_names_required_ci_check() -> None:
    """The README names the exact CI check that must pass before merge."""
    assert REQUIRED_CHECK_NAME in _readme_text()


def test_readme_states_no_direct_pushes() -> None:
    """The README states that direct pushes to ``main`` are disallowed."""
    lowered = _readme_text().lower()
    assert "direct push" in lowered or "no direct" in lowered or "cannot push" in lowered


def test_setup_script_exists_and_executable() -> None:
    """A re-apply script exists and is marked executable."""
    assert SETUP_SCRIPT.is_file()
    mode = SETUP_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "setup_branch_protection.sh must be executable"


def test_setup_script_references_required_check() -> None:
    """The script references the exact required-check name as a constant."""
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert REQUIRED_CHECK_NAME in text


def test_setup_script_does_not_disable_admin_or_require_reviews() -> None:
    """The script must keep the autonomous merge loop working.

    ``enforce_admins`` must be false and required reviews must be null so the
    admin owner loop can still ``gh pr merge`` one PR at a time.
    """
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    # The payload is constructed via jq, so assert on the jq object fields.
    assert re.search(r"enforce_admins:\s*false", text)
    assert re.search(r"required_pull_request_reviews:\s*null", text)


def test_setup_script_has_no_hard_coded_owner_repo() -> None:
    """Owner/repo are derived at runtime, not hard-coded literals."""
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert "swalha1999/agent_debate" not in text
    assert "gh repo view" in text


def test_setup_script_contains_no_secrets() -> None:
    """The script must not embed any token/key-like material."""
    text = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert "ghp_" not in text
    assert "sk-" not in text
    assert not re.search(r"--token[= ]", text)


def test_required_check_name_matches_workflow() -> None:
    """The constant matches the ``name:`` of the CI job in the workflow."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert f"name: {REQUIRED_CHECK_NAME}" in ci


def test_setup_script_is_not_world_writable() -> None:
    """Sanity: the script is not world-writable (basic hygiene)."""
    mode = os.stat(SETUP_SCRIPT).st_mode
    assert not (mode & stat.S_IWOTH)
