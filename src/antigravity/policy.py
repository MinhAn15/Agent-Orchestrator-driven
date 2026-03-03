"""Rule-based Policy Engine for Antigravity (v0.2).

Evaluates agent actions against a set of declarative rules before execution.
Rules are expressed as Python dicts and evaluated in priority order.

Example rule::

    {
        "id": "block-delete-in-prod",
        "priority": 1,
        "condition": {"action_type": "delete", "environment": "production"},
        "effect": "deny",
        "reason": "Destructive actions are forbidden in production without approval.",
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass
class Rule:
    """A single policy rule."""

    id: str
    condition: dict[str, Any]
    effect: Effect
    priority: int = 100
    reason: str = ""

    def matches(self, context: dict[str, Any]) -> bool:
        """Return True if every key/value in condition matches the context."""
        return all(context.get(k) == v for k, v in self.condition.items())


@dataclass
class PolicyDecision:
    """Result returned by the policy engine for a given context."""

    effect: Effect
    matched_rule_id: str | None = None
    reason: str = ""

    @property
    def is_allowed(self) -> bool:
        return self.effect == Effect.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.effect == Effect.DENY

    @property
    def requires_approval(self) -> bool:
        return self.effect == Effect.REQUIRE_APPROVAL


@dataclass
class PolicyEngine:
    """Evaluates a context against an ordered list of rules.

    Rules are sorted by ascending priority (lower number = higher precedence).
    The first matching rule wins. If no rule matches, the default effect applies.
    """

    rules: list[Rule] = field(default_factory=list)
    default_effect: Effect = Effect.ALLOW

    def add_rule(self, rule: Rule) -> None:
        """Register a rule and maintain priority order."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def evaluate(self, context: dict[str, Any]) -> PolicyDecision:
        """Evaluate context against all rules and return a decision."""
        for rule in self.rules:
            if rule.matches(context):
                return PolicyDecision(
                    effect=rule.effect,
                    matched_rule_id=rule.id,
                    reason=rule.reason,
                )
        return PolicyDecision(effect=self.default_effect, reason="No rule matched; default effect applied.")

    def load_rules(self, rules_dicts: list[dict[str, Any]]) -> None:
        """Bulk-load rules from a list of dicts (e.g., loaded from YAML/JSON)."""
        for d in rules_dicts:
            self.add_rule(
                Rule(
                    id=d["id"],
                    condition=d["condition"],
                    effect=Effect(d["effect"]),
                    priority=d.get("priority", 100),
                    reason=d.get("reason", ""),
                )
            )


# ---------------------------------------------------------------------------
# Built-in default rule set (sensible production defaults)
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "id": "block-delete-production",
        "priority": 1,
        "condition": {"action_type": "delete", "environment": "production"},
        "effect": "deny",
        "reason": "Destructive delete is forbidden in production without explicit approval.",
    },
    {
        "id": "require-approval-financial",
        "priority": 2,
        "condition": {"domain": "financial"},
        "effect": "require_approval",
        "reason": "All financial-domain actions require human approval.",
    },
    {
        "id": "block-external-exfil",
        "priority": 3,
        "condition": {"action_type": "send_external", "data_classification": "confidential"},
        "effect": "deny",
        "reason": "Sending confidential data to external systems is prohibited.",
    },
]


def create_default_engine() -> PolicyEngine:
    """Return a PolicyEngine pre-loaded with the default production rule set."""
    engine = PolicyEngine()
    engine.load_rules(DEFAULT_RULES)
    return engine
