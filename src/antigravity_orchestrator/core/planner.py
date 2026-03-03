"""Planner abstraction used to produce executable plans."""

from __future__ import annotations

from typing import Protocol

from antigravity_orchestrator.models import Task, TraceEvent


class Planner(Protocol):
    """Builds an ordered list of tasks from raw workflow input."""

    def plan(self, workflow_name: str, inputs: dict[str, object]) -> tuple[list[Task], list[TraceEvent]]:
        """Create tasks and optional planning trace events."""
