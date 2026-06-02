"""Tests for the ``agent_debate.log`` redaction processor (TASKS.md 1.4).

Written TDD-first: a structlog processor must redact secret-like values — both
by *key name* (``*key*``/``*token*``/``*secret*``/``*password*``/etc.) and by
*value pattern* (``sk-…``/``sk-ant-…``, AWS ``AKIA…``, PEM headers, bearer
tokens) regardless of key — recursing into nested dicts/lists, and truncate any
string longer than a configurable max length. The acceptance criteria (issue
#19): secret-like values never appear in console *or* JSONL output, and
oversized payloads are truncated.

The final test wires the real :func:`configure` pipeline against a tmp runs dir,
logs an event carrying a secret in its payload, then reads the JSONL file from
disk and asserts the secret string is absent while the redaction marker present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_debate.log import configure, log_event
from agent_debate.log.redaction import (
    MAX_VALUE_LEN,
    REDACTED,
    TRUNCATED_SUFFIX,
    make_redactor,
    redact_event,
)

_ANTHROPIC_SECRET = "sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_OPENAI_SECRET = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"


def _process(event_dict: dict[str, Any]) -> dict[str, Any]:
    """Run the default redactor over ``event_dict`` (logger/method unused)."""
    return dict(redact_event(None, "info", event_dict))


def test_redacts_value_by_secret_key_name() -> None:
    """A value under a secret-like key (api_key) is replaced with the marker."""
    out = _process({"api_key": "totally-secret-value"})
    assert out["api_key"] == REDACTED
    assert "totally-secret-value" not in json.dumps(out)


def test_redacts_token_and_password_and_secret_keys() -> None:
    """``token``/``password``/``secret``/``authorization`` keys are redacted."""
    out = _process(
        {
            "access_token": "abc123",
            "user_password": "hunter2",
            "client_secret": "shh",
            "Authorization": "Bearer xyz",
        }
    )
    assert out["access_token"] == REDACTED
    assert out["user_password"] == REDACTED
    assert out["client_secret"] == REDACTED
    assert out["Authorization"] == REDACTED


def test_redacts_secret_value_under_non_secret_key() -> None:
    """An ``sk-ant-…`` value is redacted even under an innocuous key name."""
    out = _process({"note": f"the key is {_ANTHROPIC_SECRET} keep safe"})
    assert _ANTHROPIC_SECRET not in json.dumps(out)
    assert REDACTED in str(out["note"])


def test_redacts_openai_aws_and_pem_value_patterns() -> None:
    """openai ``sk-…``, AWS ``AKIA…`` and PEM headers are redacted by value."""
    pem = "-----BEGIN RSA PRIVATE KEY-----"
    out = _process({"a": _OPENAI_SECRET, "b": _AWS_KEY, "c": pem})
    dumped = json.dumps(out)
    assert _OPENAI_SECRET not in dumped
    assert _AWS_KEY not in dumped
    assert pem not in dumped


def test_recurses_into_nested_dicts_and_lists() -> None:
    """Redaction applies recursively into nested payload dicts and lists."""
    out = _process(
        {
            "payload": {
                "messages": [
                    {"api_key": "leak-me"},
                    {"text": f"hi {_ANTHROPIC_SECRET}"},
                ],
                "nested": {"deep": {"token": "deep-leak"}},
            }
        }
    )
    dumped = json.dumps(out)
    assert "leak-me" not in dumped
    assert "deep-leak" not in dumped
    assert _ANTHROPIC_SECRET not in dumped


def test_truncates_long_string_at_configured_length() -> None:
    """A string longer than the max length is truncated with the marker."""
    long_value = "x" * (MAX_VALUE_LEN + 50)
    out = _process({"blob": long_value})
    blob = out["blob"]
    assert isinstance(blob, str)
    assert blob.endswith(TRUNCATED_SUFFIX)
    assert len(blob) == MAX_VALUE_LEN + len(TRUNCATED_SUFFIX)


def test_short_string_is_not_truncated() -> None:
    """A string at or below the max length is left untouched."""
    out = _process({"blob": "short value"})
    assert out["blob"] == "short value"


def test_make_redactor_custom_max_len_truncates_earlier() -> None:
    """The factory honours a custom max length for truncation."""
    redactor = make_redactor(max_len=4)
    out = redactor(None, "info", {"blob": "abcdefgh"})
    blob = out["blob"]
    assert isinstance(blob, str)
    assert blob == "abcd" + TRUNCATED_SUFFIX


def test_safe_count_key_tokens_not_redacted() -> None:
    """The LogEvent ``tokens`` count is allowlisted despite containing 'token'."""
    out = _process({"tokens": 128, "token_count": 5})
    assert out["tokens"] == 128
    assert out["token_count"] == 5


def test_non_string_scalars_pass_through() -> None:
    """Numbers/bools/None are returned unchanged (no spurious truncation)."""
    out = _process({"n": 42, "ok": True, "none": None, "f": 1.5})
    assert out == {"n": 42, "ok": True, "none": None, "f": 1.5}


def test_pipeline_jsonl_on_disk_has_no_secret(tmp_path: Path) -> None:
    """The configured pipeline redacts secrets in the on-disk JSONL file."""
    runs_dir = tmp_path / "runs"
    log_event(
        run_id="run-secret",
        agent="pro",
        event_type="message",
        round=1,
        payload={"api_key": _ANTHROPIC_SECRET, "text": f"token {_OPENAI_SECRET}"},
        runs_dir=runs_dir,
    )
    raw = (runs_dir / "run-secret" / "run-secret.jsonl").read_text(encoding="utf-8")
    assert _ANTHROPIC_SECRET not in raw
    assert _OPENAI_SECRET not in raw
    assert REDACTED in raw


def test_pipeline_console_has_no_secret(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    """The console sink also redacts secret-like payload values."""
    configure("run-console", runs_dir=tmp_path / "runs")
    log_event(
        run_id="run-console",
        agent="con",
        event_type="message",
        round=1,
        payload={"secret": _ANTHROPIC_SECRET},
        runs_dir=tmp_path / "runs",
    )
    out = capsys.readouterr().out
    assert _ANTHROPIC_SECRET not in out
    assert REDACTED in out
