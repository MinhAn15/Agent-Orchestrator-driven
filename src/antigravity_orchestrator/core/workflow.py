"""Workflow structure primitives."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Step:
    """A step in a workflow DAG."""

    id: str
    name: str
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DependencyGraph:
    """Dependency graph describing step prerequisites."""

    nodes: dict[str, Step] = field(default_factory=dict)

    def add_step(self, step: Step) -> None:
        self.nodes[step.id] = step

    def ready_steps(self, completed_ids: set[str]) -> list[Step]:
        return [
            step
            for step in self.nodes.values()
            if step.id not in completed_ids and set(step.dependencies).issubset(completed_ids)
        ]


@dataclass(slots=True)
class WorkflowSpec:
    """Top-level workflow specification."""

    name: str
    steps: list[Step] = field(default_factory=list)

    def to_graph(self) -> DependencyGraph:
        graph = DependencyGraph()
        for step in self.steps:
            graph.add_step(step)
        return graph
