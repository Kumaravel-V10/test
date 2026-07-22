"""Workflow event stream.

The orchestrator and agents emit typed events as work happens (intent
classified, agent started, tool called, tool result, agent completed, …). A UI
can consume these live over SSE to show exactly what the fleet is doing, or a
caller can collect them into a list for a single structured response.

Design: sinks are dead simple (`emit(type, **data)`), synchronous, and never
raise into the orchestrator. Streaming is handled by :class:`QueueSink`, which
hands events to an async SSE generator via a thread-safe queue.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ─── Event type constants ───────────────────────────────────────────────
RUN_STARTED = "run.started"
ENTITIES_EXTRACTED = "entities.extracted"
ESCALATION_DETECTED = "escalation.detected"
INTENT_CLASSIFIED = "intent.classified"
AGENT_STARTED = "agent.started"
TOOL_CALLED = "tool.called"
TOOL_RESULT = "tool.result"
AGENT_COMPLETED = "agent.completed"
RUN_COMPLETED = "run.completed"
ERROR = "error"

# A stable, documented catalogue for portal integrators.
EVENT_TYPES: tuple[str, ...] = (
    RUN_STARTED, ENTITIES_EXTRACTED, ESCALATION_DETECTED, INTENT_CLASSIFIED,
    AGENT_STARTED, TOOL_CALLED, TOOL_RESULT, AGENT_COMPLETED, RUN_COMPLETED, ERROR,
)


@dataclass
class Event:
    type: str
    data: dict[str, Any]
    seq: int = 0
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "seq": self.seq, "ts": self.ts, "data": self.data}


@runtime_checkable
class EventSink(Protocol):
    def emit(self, type: str, **data: Any) -> None: ...


class NullSink:
    """Discards everything — the default when no observer is attached."""

    def emit(self, type: str, **data: Any) -> None:  # noqa: A002 - mirrors protocol
        return None


class ListSink:
    """Collects events in order (used by the synchronous /chat endpoint)."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self._seq = 0

    def emit(self, type: str, **data: Any) -> None:  # noqa: A002
        self._seq += 1
        self.events.append(Event(type=type, data=data, seq=self._seq))

    def as_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.events]


class QueueSink:
    """Pushes events onto a thread-safe queue for live SSE streaming."""

    def __init__(self, q: Any) -> None:
        self._q = q
        self._seq = 0

    def emit(self, type: str, **data: Any) -> None:  # noqa: A002
        self._seq += 1
        self._q.put(Event(type=type, data=data, seq=self._seq))
