"""No-code-execution enforcement — model/tool output never reaches a code-exec path (7.3).

PRD §5.7: *"no arbitrary code execution from model output"* (tool inputs are validated
Pydantic models). The engine consumes model output as **plain transcript text**
(``turn.py``: ``output.output`` → ``enforce_word_limit`` → ``context.append_assistant``)
and search results are sanitised (7.1/7.5) — so no model- or tool-derived string is ever
``eval``/``exec``/``compile``'d, run as a shell command, or used to build SQL.

This module turns that design property into a **test-enforced guarantee** via two checks:

* **Structural** — a source scan over ``packages/*/src`` (comments and string-literal
  *contents* stripped via :mod:`tokenize`, mirroring ``test_no_bypass.py``) asserts no
  dangerous code-execution construct (``eval(``, ``exec(``, ``compile(``, ``os.system(``,
  ``subprocess.*``, ``__import__(``, ``pickle.loads(``, unsafe ``yaml.load(``,
  ``shell=True``, or string-built SQL) appears anywhere outside a NAMED allowlist. A new
  such construct fails CI, catching a future model-output execution path.
* **Strict-typing** — every registered tool (``debater_tools()`` + ``controller_tools()``)
  takes a single **Pydantic input model**, and a malformed payload is rejected with a
  ``ValidationError`` — so unvalidated model output can never become an arbitrary tool arg.
"""

from __future__ import annotations

import io
import re
import tokenize
from pathlib import Path

import pytest
from agent_debate.core.agents import controller_tools, debater_tools
from pydantic import ValidationError
from pydantic_ai import Tool

#: Repo root — ``packages/core/tests`` is three parents below it.
_REPO_ROOT = Path(__file__).resolve().parents[3]

#: The source trees scanned for dangerous code-execution constructs.
_SRC_GLOB = "packages/*/src"

#: Dangerous constructs that could execute model/tool-derived text. Each maps a human
#: label to the regex matching the raw construct. The scan runs over the tokenised,
#: space-joined code stream (:func:`_code_only`), so attribute access reads as ``. name``;
#: the builtin patterns use a ``(?<![.\w])(?<!\.\s)`` look-behind so ``re.compile(`` (regex
#: compilation, not the builtin) and longer identifiers never false-positive.
_DANGEROUS_PATTERNS: dict[str, re.Pattern[str]] = {
    "eval": re.compile(r"(?<![.\w])(?<!\.\s)eval\s*\("),
    "exec": re.compile(r"(?<![.\w])(?<!\.\s)exec\s*\("),
    "compile_builtin": re.compile(r"(?<![.\w])(?<!\.\s)compile\s*\("),
    "dunder_import": re.compile(r"__import__\s*\("),
    "os_system": re.compile(r"\bos\.system\s*\("),
    "subprocess_call": re.compile(r"\bsubprocess\.(?:Popen|run|call|check_output|check_call)\s*\("),
    "pickle_loads": re.compile(r"\bpickle\.loads\s*\("),
    "yaml_unsafe_load": re.compile(r"\byaml\.load\s*\("),
    "shell_true": re.compile(r"\bshell\s*=\s*True\b"),
    "sql_string_build": re.compile(r"(?i)(?:SELECT|INSERT|UPDATE|DELETE)\b.*\+\s*\w"),
}

#: Allowlist: source files permitted to contain a matched construct because the use is
#: a legitimate, NON-model-output one. Empty today — the design routes no model/tool
#: output into any execution path — so the guarantee is that the set stays minimal and
#: every entry is a reviewed, non-model-output use. ``scripts/`` (dev tooling that shells
#: out to ``gh``) is intentionally OUTSIDE ``packages/*/src`` and so is never scanned.
_ALLOWLISTED_FILES: frozenset[str] = frozenset()


def _source_files() -> list[Path]:
    """All ``.py`` files under every ``packages/*/src`` tree (sorted, stable)."""
    files: list[Path] = []
    for src in sorted(_REPO_ROOT.glob(_SRC_GLOB)):
        files += sorted(src.rglob("*.py"))
    return files


def _code_only(text: str) -> str:
    """Return ``text`` with comments and string-literal *contents* stripped.

    Tokenising and dropping ``COMMENT``/``STRING`` tokens means a construct named only
    in a docstring or comment (e.g. ``eval(`` in prose) never counts — only real code.
    """
    kept: list[str] = []
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        kept += [tok.string]
    return " ".join(kept)


def _scan(code: str) -> list[str]:
    """Return the labels of every dangerous construct found in already-stripped ``code``."""
    return [label for label, pat in _DANGEROUS_PATTERNS.items() if pat.search(code)]


def test_source_tree_was_actually_scanned() -> None:
    """Guard: the scan globbed real files (a silent empty scan would pass vacuously)."""
    assert _source_files(), "expected source files under packages/*/src"


def test_scanner_detects_a_planted_violation() -> None:
    """The scanner is non-vacuous: a planted ``eval(`` / ``exec(`` in code is detected."""
    planted = "def handler(model_output):\n    return eval(model_output)\n"
    assert "eval" in _scan(_code_only(planted))
    assert _scan(_code_only("x = exec(untrusted)\n")) == ["exec"]


def test_scanner_ignores_constructs_in_comments_and_strings() -> None:
    """A construct named only in a comment or string literal is NOT a real code path."""
    assert _scan(_code_only("# do not eval(x) here\nvalue = 1\n")) == []
    assert _scan(_code_only('note = "never exec(this)"\n')) == []


def test_re_compile_is_not_flagged_as_the_builtin() -> None:
    """``re.compile(`` (regex compilation) must not false-positive as builtin ``compile(``."""
    assert _scan(_code_only("import re\np = re.compile(r'x+')\n")) == []


def test_no_code_execution_path_from_model_or_tool_output() -> None:
    """Structural: no dangerous code-execution construct appears outside the allowlist.

    Fails if a NEW ``eval(``/``exec(``/``os.system(``/``subprocess.*``/SQL-string-build
    (etc.) appears in ``packages/*/src`` — catching a future path that could execute
    model- or tool-derived text. Comments and strings are stripped first, so only real
    code counts.
    """
    offenders: dict[str, list[str]] = {}
    for path in _source_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel in _ALLOWLISTED_FILES:
            continue
        hits = _scan(_code_only(path.read_text(encoding="utf-8")))
        if hits:
            offenders[rel] = hits

    assert not offenders, (
        "dangerous code-execution constructs found outside the allowlist: "
        f"{offenders}. Model/tool output must never reach eval/exec/shell/SQL; "
        "remove the construct or add a reviewed, non-model-output entry to "
        "_ALLOWLISTED_FILES."
    )


def _all_tools() -> list[Tool[None]]:
    """Every registered tool: the debater set plus the controller set."""
    return [*debater_tools(), *controller_tools()]


def test_every_registered_tool_takes_a_single_strictly_typed_argument() -> None:
    """Each tool's sole parameter is a typed model — no untyped ``**kwargs``/arbitrary dict.

    A strictly-typed boundary means unvalidated model output cannot flow in as an
    arbitrary tool arg: pydantic-ai validates the payload against the parameter schema.
    """
    for tool in _all_tools():
        params = tool.function_schema.function.__annotations__
        typed = {name: ann for name, ann in params.items() if name != "return"}
        assert len(typed) == 1, f"{tool.name} must take exactly one typed argument, got {typed}"
        (annotation,) = typed.values()
        assert annotation not in (dict, object), f"{tool.name} arg must be strictly typed"


def test_every_registered_tool_rejects_an_unvalidated_payload() -> None:
    """A malformed payload is rejected (``ValidationError``) at every tool boundary."""
    payload = {"request": {"__unexpected__": object()}}
    for tool in _all_tools():
        with pytest.raises(ValidationError):
            tool.function_schema.validator.validate_python(payload)
