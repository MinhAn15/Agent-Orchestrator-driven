"""Basic policy engine for tool permissions, quotas, and approvals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(slots=True)
class Budget:
    max_tokens: int
    max_seconds: float
    used_tokens: int = 0
    used_seconds: float = 0.0

    def has_capacity(self, add_tokens: int = 0, add_seconds: float = 0.0) -> bool:
        return (self.used_tokens + add_tokens) <= self.max_tokens and (
            self.used_seconds + add_seconds
        ) <= self.max_seconds

    def consume(self, *, tokens: int = 0, seconds: float = 0.0) -> None:
        if not self.has_capacity(tokens, seconds):
            raise ValueError("Budget exceeded")
        self.used_tokens += tokens
        self.used_seconds += seconds


@dataclass(slots=True)
class PolicyEngine:
    """Evaluates runtime policy constraints for a given request."""

    allow_tools: set[str] = field(default_factory=set)
    deny_tools: set[str] = field(default_factory=set)
    sensitive_actions: set[str] = field(default_factory=lambda: {"delete", "transfer_funds", "exfiltrate_data"})
    budget: Budget = field(default_factory=lambda: Budget(max_tokens=100_000, max_seconds=300.0))

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "PolicyEngine":
        return cls(
            allow_tools=set(config.get("allow_tools", []) or []),
            deny_tools=set(config.get("deny_tools", []) or []),
            sensitive_actions=set(config.get("sensitive_actions", []) or []),
            budget=Budget(
                max_tokens=int(config.get("max_tokens", 100_000)),
                max_seconds=float(config.get("max_seconds", 300.0)),
            ),
        )

    def check_tool(self, tool_name: str) -> PolicyDecision:
        if tool_name in self.deny_tools:
            return PolicyDecision(False, f"Tool '{tool_name}' is explicitly denied")
        if self.allow_tools and tool_name not in self.allow_tools:
            return PolicyDecision(False, f"Tool '{tool_name}' is not in allow-list")
        return PolicyDecision(True, "Tool permitted")

    def check_budget(self, *, add_tokens: int = 0, add_seconds: float = 0.0) -> PolicyDecision:
        if not self.budget.has_capacity(add_tokens, add_seconds):
            return PolicyDecision(False, "Token/time budget exceeded")
        return PolicyDecision(True, "Budget available")

    def require_approval(self, action: str, *, approved_actions: Iterable[str] = ()) -> PolicyDecision:
        approved_set = set(approved_actions)
        if action in self.sensitive_actions and action not in approved_set:
            return PolicyDecision(False, f"Action '{action}' requires approval")
        return PolicyDecision(True, "Action permitted")
