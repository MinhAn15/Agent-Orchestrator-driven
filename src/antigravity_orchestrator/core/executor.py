"""Executor abstraction for workflow task execution."""

from __future__ import annotations

from typing import Protocol

from antigravity_orchestrator.models import ExecutionResult, Task, TraceEvent


class Executor(Protocol):
    """Executes a planned task."""

    def execute(self, task: Task) -> tuple[ExecutionResult, list[TraceEvent]]:
        """Run the task and return result with execution traces."""
