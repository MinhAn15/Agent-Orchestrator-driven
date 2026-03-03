"""Tests for the rule-based PolicyEngine (v0.2)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from antigravity.policy import (
    Effect,
    PolicyEngine,
    PolicyDecision,
    Rule,
    create_default_engine,
)


# ---------------------------------------------------------------------------
# Unit tests: Rule.matches
# ---------------------------------------------------------------------------

class TestRuleMatches:
    def test_exact_match(self):
        rule = Rule(id="r1", condition={"action_type": "delete"}, effect=Effect.DENY)
        assert rule.matches({"action_type": "delete", "env": "prod"}) is True

    def test_partial_condition_no_match(self):
        rule = Rule(
            id="r2",
            condition={"action_type": "delete", "environment": "production"},
            effect=Effect.DENY,
        )
        assert rule.matches({"action_type": "delete"}) is False

    def test_empty_condition_always_matches(self):
        rule = Rule(id="r3", condition={}, effect=Effect.ALLOW)
        assert rule.matches({}) is True
        assert rule.matches({"anything": "value"}) is True

    def test_wrong_value_no_match(self):
        rule = Rule(id="r4", condition={"env": "production"}, effect=Effect.DENY)
        assert rule.matches({"env": "staging"}) is False


# ---------------------------------------------------------------------------
# Unit tests: PolicyEngine.evaluate
# ---------------------------------------------------------------------------

class TestPolicyEngine:
    def test_default_allow_when_no_rules(self):
        engine = PolicyEngine()
        decision = engine.evaluate({"action_type": "read"})
        assert decision.effect == Effect.ALLOW
        assert decision.is_allowed is True
        assert decision.matched_rule_id is None

    def test_first_matching_rule_wins(self):
        engine = PolicyEngine()
        engine.add_rule(Rule(id="low-priority", condition={"x": "1"}, effect=Effect.ALLOW, priority=10))
        engine.add_rule(Rule(id="high-priority", condition={"x": "1"}, effect=Effect.DENY, priority=1))
        decision = engine.evaluate({"x": "1"})
        assert decision.effect == Effect.DENY
        assert decision.matched_rule_id == "high-priority"

    def test_deny_effect(self):
        engine = PolicyEngine()
        engine.add_rule(
            Rule(id="block-delete", condition={"action_type": "delete"}, effect=Effect.DENY)
        )
        decision = engine.evaluate({"action_type": "delete"})
        assert decision.is_denied is True

    def test_require_approval_effect(self):
        engine = PolicyEngine()
        engine.add_rule(
            Rule(id="fin", condition={"domain": "financial"}, effect=Effect.REQUIRE_APPROVAL)
        )
        decision = engine.evaluate({"domain": "financial", "action_type": "transfer"})
        assert decision.requires_approval is True

    def test_no_match_uses_default_effect(self):
        engine = PolicyEngine(default_effect=Effect.DENY)
        engine.add_rule(Rule(id="r1", condition={"env": "prod"}, effect=Effect.ALLOW))
        decision = engine.evaluate({"env": "staging"})
        assert decision.effect == Effect.DENY

    def test_load_rules_from_dicts(self):
        engine = PolicyEngine()
        engine.load_rules([
            {"id": "r1", "condition": {"k": "v"}, "effect": "deny", "priority": 5, "reason": "test"},
        ])
        assert len(engine.rules) == 1
        assert engine.rules[0].id == "r1"
        assert engine.rules[0].effect == Effect.DENY


# ---------------------------------------------------------------------------
# Integration tests: create_default_engine
# ---------------------------------------------------------------------------

class TestDefaultEngine:
    def setup_method(self):
        self.engine = create_default_engine()

    def test_block_delete_in_production(self):
        ctx = {"action_type": "delete", "environment": "production"}
        decision = self.engine.evaluate(ctx)
        assert decision.is_denied, "Delete in production must be denied"
        assert decision.matched_rule_id == "block-delete-production"

    def test_allow_delete_in_staging(self):
        ctx = {"action_type": "delete", "environment": "staging"}
        decision = self.engine.evaluate(ctx)
        assert decision.is_allowed, "Delete in staging should be allowed by default"

    def test_financial_domain_requires_approval(self):
        ctx = {"domain": "financial", "action_type": "transfer"}
        decision = self.engine.evaluate(ctx)
        assert decision.requires_approval, "Financial actions need approval"

    def test_block_confidential_external_send(self):
        ctx = {"action_type": "send_external", "data_classification": "confidential"}
        decision = self.engine.evaluate(ctx)
        assert decision.is_denied, "Confidential data exfiltration must be denied"

    def test_normal_read_is_allowed(self):
        ctx = {"action_type": "read", "environment": "production"}
        decision = self.engine.evaluate(ctx)
        assert decision.is_allowed, "Read action should be allowed"
