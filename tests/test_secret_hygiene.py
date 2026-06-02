"""Secret-hygiene integration test (TASKS.md 7.4, issue #58).

PRD §7.4 mandates two coordinated defences against credential leakage:

* a **build-time** gate (``scripts/secret_scan.py``) that fails CI on any
  key-like secret committed to the tree (source *and* log artifacts), and
* a **runtime** redactor (``agent_debate.log.redaction``, wired into
  :func:`agent_debate.log.configure`) that strips secrets before they reach
  either sink, so they never land in ``runs/<run_id>.jsonl``.

This test proves the two layers are coordinated against one planted fake key:

* (a) **LOG redaction** — log an event whose payload carries the fake key,
  read the on-disk JSONL back, and assert the key is ABSENT while the
  redaction marker is PRESENT (it was never logged).
* (b) **Secret scan** — write the same fake key into a tmp file and a tmp
  ``runs/*.jsonl`` artifact and assert the scanner FLAGS both (logs are in
  the scan's coverage, not silently skipped).

The fake key is assembled at runtime from string PARTS so the literal pattern
never appears as a committed source token — keeping the live CI secret-scan
gate green while still exercising every detector. The final test re-runs the
real-tree scan to confirm exit 0.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from agent_debate.log import REDACTED, log_event

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "secret_scan.py"

#: Built from parts at runtime so the committed source carries no ``sk-ant-…``
#: literal that the live tree scan would (correctly) flag. Matches the shared
#: ``sk-ant-…`` detector used by BOTH redaction and the scanner.
FAKE_KEY = "sk-" + "ant-" + "FAKEKEY" + "0123456789ABCDEFGHIJ"


def _load_scanner() -> ModuleType:
    """Import the standalone scanner by path (``scripts/`` is not a package)."""
    spec = importlib.util.spec_from_file_location("secret_scan", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_redaction_keeps_planted_key_out_of_jsonl(tmp_path: Path) -> None:
    """(a) The planted key never reaches the on-disk run log; marker present."""
    runs_dir = tmp_path / "runs"
    log_event(
        run_id="hygiene-1",
        round=1,
        agent="pro",
        event_type="tool_call",
        payload={"api_key": FAKE_KEY, "note": f"leaked {FAKE_KEY} here"},
        runs_dir=runs_dir,
    )

    raw = (runs_dir / "hygiene-1" / "hygiene-1.jsonl").read_text(encoding="utf-8")
    assert FAKE_KEY not in raw, "redaction must keep the secret out of the JSONL"
    assert REDACTED in raw

    record = json.loads(raw.splitlines()[0])
    assert record["payload"]["api_key"] == REDACTED


def test_scan_flags_planted_key_in_source_file(tmp_path: Path) -> None:
    """(b) The scanner flags the planted key in a source-like tmp file."""
    mod = _load_scanner()
    leak = tmp_path / "leak.py"
    leak.write_text(f'KEY = "{FAKE_KEY}"\n', encoding="utf-8")
    assert mod.find_secrets(tmp_path), "scanner must flag the planted source key"


def test_scan_covers_committed_log_artifacts(tmp_path: Path) -> None:
    """The scan's coverage includes ``runs/*.jsonl`` log artifacts, not just code."""
    mod = _load_scanner()
    assert ".jsonl" in mod.SCANNED_SUFFIXES, "log files must be in scan coverage"

    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "leaked.jsonl").write_text(
        json.dumps({"payload": {"api_key": FAKE_KEY}}) + "\n", encoding="utf-8"
    )
    findings = mod.find_secrets(tmp_path)
    assert any(path.name == "leaked.jsonl" for path, _label, _secret in findings)


def test_scan_and_redaction_share_the_key_detector(tmp_path: Path) -> None:
    """Both layers catch the SAME planted key (coordination, not coincidence)."""
    mod = _load_scanner()
    assert mod.scan_text(FAKE_KEY), "scan layer must detect the key"

    runs_dir = tmp_path / "runs"
    log_event(
        run_id="hygiene-2",
        round=1,
        agent="con",
        event_type="message",
        payload={"text": FAKE_KEY},
        runs_dir=runs_dir,
    )
    raw = (runs_dir / "hygiene-2" / "hygiene-2.jsonl").read_text(encoding="utf-8")
    assert FAKE_KEY not in raw and REDACTED in raw


def test_live_tree_scan_stays_clean() -> None:
    """The committed tree (incl. this test's runtime-built key) still exits 0."""
    mod = _load_scanner()
    assert mod.main([]) == 0
