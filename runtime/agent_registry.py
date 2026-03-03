"""Agent registry for role-based lookup and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Mapping, MutableMapping, Protocol


class AgentRole(str, Enum):
    """Canonical roles supported by the orchestrator runtime."""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"


class Agent(Protocol):
    """Protocol for agents registered in the runtime."""

    name: str

    def run(self, task_state: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run the agent with the current task state and return an update."""


AgentFactory = Callable[[], Agent]


@dataclass(slots=True)
class AgentRegistry:
    """Registry keyed by role for agent discovery and instantiation."""

    _factories: MutableMapping[AgentRole, Dict[str, AgentFactory]] = field(default_factory=dict)

    def register(self, role: AgentRole | str, agent_name: str, factory: AgentFactory) -> None:
        """Register a named agent factory under a given role."""

        normalized = AgentRole(role)
        self._factories.setdefault(normalized, {})[agent_name] = factory

    def unregister(self, role: AgentRole | str, agent_name: str) -> None:
        """Remove an agent from a role-specific registry if present."""

        normalized = AgentRole(role)
        if normalized in self._factories:
            self._factories[normalized].pop(agent_name, None)
            if not self._factories[normalized]:
                self._factories.pop(normalized, None)

    def create(self, role: AgentRole | str, agent_name: str) -> Agent:
        """Instantiate a registered agent by role and name."""

        normalized = AgentRole(role)
        if normalized not in self._factories or agent_name not in self._factories[normalized]:
            known = ", ".join(self.list_agents(normalized)) or "<none>"
            raise KeyError(
                f"Unknown agent '{agent_name}' for role '{normalized.value}'. Known agents: {known}"
            )
        return self._factories[normalized][agent_name]()

    def list_agents(self, role: AgentRole | str) -> tuple[str, ...]:
        """List registered agent names for a role."""

        normalized = AgentRole(role)
        return tuple(sorted(self._factories.get(normalized, {}).keys()))

    def snapshot(self) -> Dict[str, tuple[str, ...]]:
        """Return a serializable snapshot of current role→agent mappings."""

        return {role.value: tuple(sorted(agents.keys())) for role, agents in self._factories.items()}
