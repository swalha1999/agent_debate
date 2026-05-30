"""Contract tests for ``.env.example`` and ``.gitignore`` (TASKS.md 0.7).

These lock two repo-hygiene invariants required by the PRD and the build
guidelines:

* ``.env.example`` documents **every** configuration variable from PRD §7 so a
  new contributor can copy it to ``.env`` and know what to set.
* ``.env`` (the real, secret-bearing file) is git-ignored so credentials are
  never committed, and ``.env.example`` itself carries no real secrets.

The PRD §7 variable list is mirrored here as a maintained constant; if PRD §7
changes, update :data:`PRD_SECTION_7_VARS` and ``.env.example`` together.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"
GITIGNORE = REPO_ROOT / ".gitignore"

# Authoritative list from docs/PRD.md §7 "Configuration (env)".
PRD_SECTION_7_VARS = (
    "ANTHROPIC_API_KEY",
    "DEBATER_MODEL",
    "CONTROLLER_MODEL",
    "PRO_MODEL",
    "CON_MODEL",
    "ROUNDS",
    "MAX_WORDS",
    "TURN_TIMEOUT_S",
    "MAX_RETRIES",
    "SEARCH_BACKEND",
    "SEARCH_API_KEY",
)

# Paths/patterns the .gitignore must cover (incl. the secret .env file).
REQUIRED_GITIGNORE_PATTERNS = (
    ".venv",
    "__pycache__",
    "*.pyc",
    ".env",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
)


def _env_example_assignments() -> dict[str, str]:
    """Parse ``KEY=value`` lines from ``.env.example`` (ignoring comments)."""
    assignments: dict[str, str] = {}
    for raw in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        assignments[key.strip()] = value.strip()
    return assignments


def test_env_example_exists() -> None:
    """A committed ``.env.example`` template must exist."""
    assert ENV_EXAMPLE.is_file()


def test_env_example_covers_every_prd_section_7_var() -> None:
    """Every PRD §7 variable is assigned in ``.env.example``."""
    assignments = _env_example_assignments()
    missing = [var for var in PRD_SECTION_7_VARS if var not in assignments]
    assert not missing, f"PRD §7 vars missing from .env.example: {missing}"


def test_env_example_has_no_real_secrets() -> None:
    """The secret-bearing keys carry placeholders, not real credentials."""
    assignments = _env_example_assignments()
    api_key = assignments.get("ANTHROPIC_API_KEY", "")
    # A real Anthropic key is a long ``sk-ant-...`` token; a placeholder is short
    # and/or obviously fake. Reject anything that looks like a live key.
    assert not (api_key.startswith("sk-ant-") and len(api_key) > 25), (
        "ANTHROPIC_API_KEY in .env.example looks like a real secret"
    )
    assert assignments.get("SEARCH_API_KEY", "") == ""


def test_gitignore_covers_required_patterns() -> None:
    """``.gitignore`` ignores caches, build dirs, and the secret ``.env``."""
    lines = {
        line.strip().rstrip("/")
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    missing = [
        pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern.rstrip("/") not in lines
    ]
    assert not missing, f".gitignore missing required patterns: {missing}"


def test_gitignore_ignores_dotenv_but_not_example() -> None:
    """``.env`` is ignored while the committed ``.env.example`` is not."""
    lines = {
        line.strip()
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    assert ".env" in lines
    assert ".env.example" not in lines
    assert "*.env" not in lines
