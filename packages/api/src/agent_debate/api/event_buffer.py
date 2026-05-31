"""Per-run live event buffer for SSE streaming (task 10.3, issue #70).

The SSE endpoint (``GET /debates/{id}/stream``) must stream a debate's events AS
THEY HAPPEN, yet the run executes on a background worker (task 10.2). This tiny
thread-safe buffer is the hand-off between them: the streaming runner appends
each :class:`~agent_debate.log.LogEvent` via :meth:`publish` (the live producer),
the SSE consumer drains them via :meth:`stream` (a blocking iterator), and
:meth:`close` marks completion so the consumer's iterator terminates.

Concurrency (documented). A single :class:`threading.Condition` guards an
append-only list plus a ``closed`` flag. Producers append + notify; the consumer
waits for either a new event or ``closed``. The list is append-only and never
truncated, so a run that finished *before* a consumer connects is faithfully
REPLAYED (the consumer reads all events from index 0, then sees ``closed`` and
stops) — the same code path serves live and replay. No event is dropped or
double-counted because each consumer tracks its own read cursor.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

from agent_debate.log import LogEvent


class EventBuffer:
    """A thread-safe, append-only buffer of a run's :class:`LogEvent` stream.

    Supports one producer (the streaming runner) and many independent consumers
    (each SSE connection), with live tailing and faithful replay after close.
    """

    def __init__(self) -> None:
        """Create an empty, open buffer with its producer/consumer lock."""
        self._events: list[LogEvent] = []
        self._closed = False
        self._cond = threading.Condition()

    def publish(self, event: LogEvent) -> None:
        """Append ``event`` and wake any waiting consumers (producer side)."""
        with self._cond:
            self._events.append(event)
            self._cond.notify_all()

    def close(self) -> None:
        """Mark the stream complete so consumer iterators terminate."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def stream(self) -> Iterator[LogEvent]:
        """Yield every event in order (blocking for live ones) until closed.

        Replays all buffered events from the start, then blocks for new ones,
        returning once the buffer is :meth:`close`-d and fully drained.
        """
        index = 0
        while True:
            with self._cond:
                while index >= len(self._events) and not self._closed:
                    self._cond.wait()
                if index >= len(self._events) and self._closed:
                    return
                event = self._events[index]
            index += 1
            yield event


__all__ = ["EventBuffer"]
