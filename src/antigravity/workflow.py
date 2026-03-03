"""Core workflow primitives used by orchestration runtime."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowGraph:
    """Very small placeholder graph model for test scaffolding."""

    nodes: tuple[str, ...] = ()


def should_retry(attempt: int, max_retries: int) -> bool:
    """Return True when another retry should be performed."""

    return attempt < max_retries
