"""Canonical data contracts for orchestration runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Task:
    """A single unit of work in a workflow."""

    id: str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolCall:
    """A normalized call to an external tool."""

    id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentAction:
    """Action chosen by an agent to progress execution."""

    task_id: str
    summary: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class ExecutionResult:
    """Execution status and output for a task or workflow run."""

    run_id: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class TraceEvent:
    """Structured event emitted during planning/execution."""

    event_type: str
    message: str
    run_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
