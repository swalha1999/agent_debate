"""Shared fixtures + stub engines for the Epic-9 CLI acceptance pass (issue #67).

Split out of :mod:`test_cli_acceptance` (PRD §3.2: split, don't compress) so the
acceptance module stays under the 150-line cap. These stubs stand in for
:class:`~agent_debate.core.DebateEngine` so the acceptance tests drive the CLI
END-TO-END with NO network / API key — the real SDK already routes every model
call through the Epic-13 gatekeeper; the CLI only consumes ``run`` / ``stream``.
"""

from __future__ import annotations

from collections.abc import Iterator

import agent_debate.cli.app as cli_app
import pytest
from agent_debate.core import DebateConfig, MissingApiKeyError, Settings
from agent_debate.core.engine.result import DebateResult
from agent_debate.core.skills.models import DebateSide, Verdict
from agent_debate.log import LogEvent

#: A known, fixed config so assertions read from config, not hard-coded numbers.
FIXED_ROUNDS = 7
FIXED_MAX_WORDS = 42
FIXED_BACKEND = "duckduckgo"

PRO_TEXT = "pro opening statement"
CON_TEXT = "con rebuttal point"
VERDICT_SUMMARY = "pro prevailed"
VERDICT_RATIONALE = "tighter reasoning"


def make_result(topic: str) -> DebateResult:
    """A canned :class:`DebateResult` with a decided verdict for ``topic``."""
    return DebateResult(
        topic=topic,
        verdict=Verdict(
            winner=DebateSide.PRO,
            rationale=VERDICT_RATIONALE,
            scores={DebateSide.PRO: 2.0, DebateSide.CON: 1.0},
            summary=VERDICT_SUMMARY,
        ),
    )


def _message(side: DebateSide, content: str) -> dict[str, object]:
    return {"content": content, "word_count": len(content.split())}


class RecordingEngine:
    """Stub engine recording its config/topic and streaming Pro + Con + verdict."""

    last_config: DebateConfig | None = None
    last_topic: str | None = None
    last_settings: Settings | None = None

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        type(self).last_config = config
        type(self).last_settings = kwargs.get("settings")  # type: ignore[assignment]

    def stream(self, topic: str) -> Iterator[object]:
        type(self).last_topic = topic
        yield LogEvent(
            run_id="r",
            round=1,
            agent=DebateSide.PRO.value,
            event_type="message",
            payload=_message(DebateSide.PRO, PRO_TEXT),
        )
        yield LogEvent(
            run_id="r",
            round=1,
            agent=DebateSide.CON.value,
            event_type="message",
            payload=_message(DebateSide.CON, CON_TEXT),
        )
        yield LogEvent(
            run_id="r",
            round=0,
            agent="controller",
            event_type="verdict",
            payload={
                "winner": DebateSide.PRO.value,
                "summary": VERDICT_SUMMARY,
                "rationale": VERDICT_RATIONALE,
            },
        )
        yield make_result(topic)

    def run(self, topic: str) -> DebateResult:
        type(self).last_topic = topic
        return make_result(topic)


class FailingEngine:
    """Stub whose ``run``/``stream`` raise a known debate failure (missing key)."""

    def __init__(self, config: DebateConfig | None = None, **kwargs: object) -> None:
        pass

    def run(self, topic: str) -> DebateResult:
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set")

    def stream(self, topic: str) -> Iterator[object]:
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set")
        yield  # pragma: no cover — generator marker; never reached.


@pytest.fixture(autouse=True)
def patch_engine(monkeypatch: pytest.MonkeyPatch) -> type[RecordingEngine]:
    """Swap in the recording stub + freeze a known ``Settings`` (no network/key)."""
    RecordingEngine.last_config = None
    RecordingEngine.last_topic = None
    RecordingEngine.last_settings = None
    monkeypatch.setattr(cli_app, "DebateEngine", RecordingEngine)
    fixed = Settings(rounds=FIXED_ROUNDS, max_words=FIXED_MAX_WORDS, search_backend=FIXED_BACKEND)
    monkeypatch.setattr(cli_app, "get_settings", lambda: fixed)
    return RecordingEngine
