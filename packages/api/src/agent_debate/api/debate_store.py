"""In-memory debate job store + status enum (task 10.2, issue #69).

PRD §6: ``POST /debates`` starts a run and ``GET /debates/{id}`` reports its
status/result. This module is the tiny state layer behind those routes: a
thread-safe in-process dict mapping ``run_id`` -> :class:`DebateRecord`.

Storage choice (documented). The store is **in-memory only** — persistence
beyond the process (a DB/queue) is out of scope here. Records are mutated under a
lock so a background worker can flip a run from ``running`` to ``done``/``failed``
while a concurrent ``GET`` reads it safely. Status strings are an
:class:`enum.StrEnum` (no inline magic — guideline §7.2), so they serialise as
plain JSON strings yet stay a single source of truth.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import StrEnum

from agent_debate.api.event_buffer import EventBuffer
from agent_debate.core import DebateResult


class DebateStatus(StrEnum):
    """Lifecycle state of a debate run (serialises to its plain string value)."""

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class DebateRecord:
    """One run's state: its status and, when finished, its result/error.

    Attributes:
        run_id: The run's unique identifier (uuid4 hex).
        status: Current :class:`DebateStatus`.
        result: The completed :class:`DebateResult`, or ``None`` until done.
        error: A short error message when ``status`` is ``failed``.
        events: Per-run live event buffer the SSE endpoint (10.3) streams from;
            the streaming runner publishes each event here as it happens.
    """

    run_id: str
    status: DebateStatus = DebateStatus.RUNNING
    result: DebateResult | None = None
    error: str | None = None
    events: EventBuffer = field(default_factory=EventBuffer)


@dataclass
class DebateStore:
    """Thread-safe in-memory map of ``run_id`` -> :class:`DebateRecord`."""

    _records: dict[str, DebateRecord] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def create(self, run_id: str) -> DebateRecord:
        """Register a new ``running`` record for ``run_id`` and return it."""
        record = DebateRecord(run_id=run_id)
        with self._lock:
            self._records[run_id] = record
        return record

    def get(self, run_id: str) -> DebateRecord | None:
        """Return the record for ``run_id``, or ``None`` if unknown."""
        with self._lock:
            return self._records.get(run_id)

    def mark_done(self, run_id: str, result: DebateResult) -> None:
        """Flip ``run_id`` to ``done``, store its ``result``, close its buffer."""
        with self._lock:
            record = self._records[run_id]
            record.status = DebateStatus.DONE
            record.result = result
        record.events.close()

    def mark_failed(self, run_id: str, error: str) -> None:
        """Flip ``run_id`` to ``failed``, store ``error``, close its buffer."""
        with self._lock:
            record = self._records[run_id]
            record.status = DebateStatus.FAILED
            record.error = error
        record.events.close()


__all__ = ["DebateRecord", "DebateStatus", "DebateStore"]
