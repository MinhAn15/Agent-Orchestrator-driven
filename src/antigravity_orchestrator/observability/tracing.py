"""Tracing primitives for orchestrator observability.

This module provides a small, dependency-light trace event model and emitter
that can be integrated with any runner/executor loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class TraceEvent:
    """A single trace event emitted during workflow execution."""

    trace_id: str
    span_id: str
    event_type: str
    workflow_name: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str | None = None
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TraceEmitter:
    """In-memory event emitter suitable for tests and local benchmarking."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> TraceEvent:
        """Persist and return a trace event."""
        self._events.append(event)
        return event

    def all_events(self) -> list[TraceEvent]:
        """Return all emitted events."""
        return [*self._events]

    def clear(self) -> None:
        """Clear all buffered events."""
        self._events.clear()
