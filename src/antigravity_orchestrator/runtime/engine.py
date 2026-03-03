"""Opinionated runtime engine for deterministic Antigravity orchestration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable
from uuid import uuid4

from antigravity.memory import InMemoryBackend, MemoryBackend
from antigravity.policy import PolicyDecision, PolicyEngine, create_default_engine
from antigravity_orchestrator.models import ExecutionResult

ActionHandler = Callable[[dict[str, Any]], dict[str, Any]]


class FixedOrchestrator:
    """One-call orchestrator with safe defaults for Antigravity users.

    The engine intentionally keeps behavior deterministic:
    - built-in default policy rules
    - in-memory state backend unless overridden
    - explicit action registration
    """

    def __init__(
        self,
        *,
        policy_engine: PolicyEngine | None = None,
        memory_backend: MemoryBackend | None = None,
    ) -> None:
        self.policy_engine = policy_engine or create_default_engine()
        self.memory_backend = memory_backend or InMemoryBackend()
        self._handlers: dict[str, ActionHandler] = {}

    def register_action(self, action_type: str, handler: ActionHandler) -> None:
        """Register an action handler for orchestrated execution."""
        self._handlers[action_type] = handler

    def run(self, workflow_name: str, payload: dict[str, Any]) -> ExecutionResult:
        """Evaluate policy, execute action, and persist run state."""
        run_id = str(uuid4())
        action_type = str(payload.get("action_type", "read"))

        decision = self.policy_engine.evaluate(payload)
        if not decision.is_allowed:
            result = self._decision_result(run_id, workflow_name, payload, decision)
            self._save_result(workflow_name, run_id, result)
            return result

        handler = self._handlers.get(action_type, self._default_handler)
        output = handler(payload)
        result = ExecutionResult(run_id=run_id, status="completed", output=output)
        self._save_result(workflow_name, run_id, result)
        return result

    def _default_handler(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "message": "Action executed with default deterministic handler.",
            "input": payload,
        }

    def _decision_result(
        self,
        run_id: str,
        workflow_name: str,
        payload: dict[str, Any],
        decision: PolicyDecision,
    ) -> ExecutionResult:
        status = "requires_approval" if decision.requires_approval else "blocked"
        return ExecutionResult(
            run_id=run_id,
            status=status,
            error=decision.reason,
            output={
                "workflow": workflow_name,
                "inputs": payload,
                "effect": decision.effect.value,
                "matched_rule_id": decision.matched_rule_id,
            },
        )

    def _save_result(self, workflow_name: str, run_id: str, result: ExecutionResult) -> None:
        self.memory_backend.set(workflow_name, run_id, asdict(result))
