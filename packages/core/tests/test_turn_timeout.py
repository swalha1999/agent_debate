"""Tests for the per-turn timeout + retry wrapper (issue #49, task 6.4).

TDD-first: these assert the §4 turn-resilience contract before the wrapper
(:func:`generate_turn_output` / :class:`TurnFailedError`) exists. The wrapper
bounds every model call by ``config.turn_timeout_s`` (cancel on timeout via the
thread-based timeout helper), retries transient failures up to
``config.max_retries`` with exponential backoff (reusing the gatekeeper's retry
policy), logs a ``timeout`` event per timeout and a ``retry`` event per retry,
and after exhaustion raises :class:`TurnFailedError` so the turn is marked FAILED
and the controller is informed — without crashing the debate.

Everything runs offline and FAST: a fake gatekeeper invokes the call inline, a
fake clock decides timeouts (no real threads/sleeping), and ``sleep_fn`` is an
injected no-op seam that records backoff delays (asserted, never slept).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from agent_debate.core.engine._call import TurnFailedError, generate_turn_output
from agent_debate.core.engine.models import DebateConfig
from agent_debate.core.settings import Settings


def _config(*, turn_timeout_s: int = 30, max_retries: int = 2) -> DebateConfig:
    """A small config built from explicit settings (config-driven, no hard-coding)."""
    settings = Settings(turn_timeout_s=turn_timeout_s, max_retries=max_retries)
    return DebateConfig.from_settings(settings)


class _InlineGatekeeper:
    """A fake gatekeeper that runs ``api_call`` inline (every call routes through it)."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, api_call: Any, *args: Any, service: str = "default", **kwargs: Any) -> Any:
        self.calls += 1
        return api_call(*args, **kwargs)


def _events(runs_dir: Path, run_id: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (runs_dir / f"{run_id}.jsonl").read_text().splitlines()]


def _call(
    keeper: _InlineGatekeeper, fn: Any, config: DebateConfig, run_id: str, runs_dir: Path, **kw: Any
) -> Any:
    """Drive the wrapper with the test seams (sleep_fn/timeout_runner via ``kw``)."""
    return generate_turn_output(
        keeper,
        fn,
        message_history=[],
        service="anthropic",
        config=config,
        run_id=run_id,
        round_=1,
        agent="pro",
        runs_dir=runs_dir,
        **kw,
    )


def _timeout_n_times(n: int) -> Any:
    """A timeout-runner seam that raises ``TimeoutError`` the first ``n`` calls."""
    state = {"left": n}

    def _runner(call: Any, timeout_s: float) -> Any:
        if state["left"] > 0:
            state["left"] -= 1
            raise TimeoutError(f"call exceeded {timeout_s}s")
        return call()

    return _runner


def test_hanging_call_times_out_then_retries(tmp_path: Path) -> None:
    """A call that hangs past the timeout raises TimeoutError, logs a timeout, then retries."""
    runs_dir = Path(str(tmp_path))
    keeper = _InlineGatekeeper()
    delays: list[float] = []
    result = _call(
        keeper,
        lambda **_: "ok",
        _config(turn_timeout_s=30, max_retries=2),
        "t1",
        runs_dir,
        sleep_fn=delays.append,
        timeout_runner=_timeout_n_times(1),
    )
    assert result == "ok"
    assert keeper.calls == 1  # first attempt cancelled before execute; retry reached it
    events = _events(runs_dir, "t1")
    assert any(e["event_type"] == "timeout" for e in events)
    assert any(e["event_type"] == "retry" for e in events)
    assert delays, "expected a backoff delay scheduled via the injected sleep_fn (no real sleep)"


def test_succeeds_on_retry_returns_result(tmp_path: Path) -> None:
    """A call that fails twice then succeeds returns the result within max_retries."""
    runs_dir = Path(str(tmp_path))
    keeper = _InlineGatekeeper()
    delays: list[float] = []
    result = _call(
        keeper,
        lambda **_: "recovered",
        _config(turn_timeout_s=30, max_retries=3),
        "t2",
        runs_dir,
        sleep_fn=delays.append,
        timeout_runner=_timeout_n_times(2),
    )
    assert result == "recovered"
    assert keeper.calls == 1  # two timeouts cancelled before execute; the third reached it
    # Exponential backoff: retry 1 then retry 2 schedule increasing delays (config-driven).
    assert len(delays) == 2
    assert delays[1] > delays[0]


def test_exhausting_retries_raises_turn_failed_and_informs_controller(tmp_path: Path) -> None:
    """All retries timing out raises TurnFailedError + logs a system event for the controller."""
    runs_dir = Path(str(tmp_path))
    keeper = _InlineGatekeeper()
    with pytest.raises(TurnFailedError):
        _call(
            keeper,
            lambda **_: "never",
            _config(turn_timeout_s=30, max_retries=2),
            "t3",
            runs_dir,
            sleep_fn=lambda _d: None,
            timeout_runner=_timeout_n_times(99),
        )
    assert keeper.calls == 0  # every attempt (1 + 2 retries) timed out before execute
    events = _events(runs_dir, "t3")
    system = [e for e in events if e["event_type"] == "system"]
    assert any(e["payload"].get("turn_failed") for e in system), "controller must be informed"


def test_non_transient_error_is_not_retried(tmp_path: Path) -> None:
    """A non-transient error (ValueError) is not retried — it propagates immediately."""
    runs_dir = Path(str(tmp_path))
    keeper = _InlineGatekeeper()

    def _boom(**_: Any) -> str:
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        _call(
            keeper,
            _boom,
            _config(max_retries=3),
            "t4",
            runs_dir,
            sleep_fn=lambda _d: None,
            timeout_runner=lambda call, _t: call(),
        )
    assert keeper.calls == 1  # no retries on a permanent error


def test_failed_turn_does_not_crash_the_debate(tmp_path: Path) -> None:
    """A turn whose model call always times out is marked FAILED; the loop continues."""
    from agent_debate.core import DebateSide, Settings, setup_debate
    from agent_debate.core.engine import run_debate_loop
    from pydantic_ai.models.test import TestModel

    runs_dir = Path(str(tmp_path))
    # max_retries=0 so the failure is immediate — no real backoff sleep in the loop
    # (which has no sleep_fn seam); the turn-failed path is what we exercise here.
    config = DebateConfig.from_settings(Settings(rounds=1, max_words=50, max_retries=0))

    class _AlwaysTimesOut:
        """A gatekeeper whose every execute call raises a transient TimeoutError."""

        def execute(self, *_a: Any, service: str = "default", **_k: Any) -> Any:
            raise TimeoutError("model hung")

    setup = setup_debate(
        "Should remote work be the default?",
        config,
        models={
            DebateSide.PRO: TestModel(),
            DebateSide.CON: TestModel(),
            "controller": TestModel(),
        },
    )
    result = run_debate_loop(
        setup, config, gatekeeper=_AlwaysTimesOut(), run_id="t6", runs_dir=runs_dir
    )
    # The debate did not crash; both turns are recorded and marked FAILED.
    assert len(result.transcript) == 2
    assert all(m.failed for m in result.transcript)
    events = _events(runs_dir, "t6")
    assert any(e["event_type"] == "system" and e["payload"].get("turn_failed") for e in events), (
        "controller informed of the failed turns"
    )


def test_call_routes_through_gatekeeper(tmp_path: Path) -> None:
    """The wrapped call still routes through the gatekeeper (every external call does)."""
    runs_dir = Path(str(tmp_path))
    keeper = _InlineGatekeeper()
    result = _call(
        keeper,
        lambda **_: "via-gate",
        _config(),
        "t5",
        runs_dir,
        timeout_runner=lambda call, _t: call(),
    )
    assert result == "via-gate"
    assert keeper.calls == 1
