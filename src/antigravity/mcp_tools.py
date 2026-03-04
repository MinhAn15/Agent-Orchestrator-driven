"""MCP tool registry for Antigravity orchestrator interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from antigravity.adhoc import AdHocOrchestrator
from antigravity.memory import InMemoryBackend, MemoryBackend
from antigravity_orchestrator.runtime import FixedOrchestrator

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]

RUN_WORKFLOW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "template": {"type": "string", "description": "Template slug to execute."},
        "vars": {
            "type": "object",
            "description": "Template render variables.",
            "additionalProperties": {"type": "string"},
            "default": {},
        },
        "context": {
            "type": "object",
            "description": "Execution context forwarded to policy evaluation.",
            "additionalProperties": True,
            "default": {},
        },
    },
    "required": ["template"],
    "additionalProperties": False,
}

INSPECT_STATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "namespace": {"type": "string"},
        "key": {"type": "string"},
    },
    "required": ["namespace", "key"],
    "additionalProperties": False,
}

HANDOFF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "from_agent": {"type": "string"},
        "to_agent": {"type": "string"},
        "task_id": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["from_agent", "to_agent", "task_id", "reason"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata and behavior for one MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


class MCPToolRegistry:
    """Registry with MCP-compatible tool metadata and call handlers."""

    def __init__(self, memory: MemoryBackend | None = None) -> None:
        self.memory = memory or InMemoryBackend()
        self.adhoc_orchestrator = AdHocOrchestrator(memory=self.memory)
        self.fixed_orchestrator = FixedOrchestrator(memory_backend=self.memory)
        self._tools: dict[str, ToolDefinition] = {
            "run_workflow": ToolDefinition(
                name="run_workflow",
                description="Run an ad-hoc workflow template and persist step-by-step state.",
                input_schema=RUN_WORKFLOW_SCHEMA,
                handler=self._handle_run_workflow,
            ),
            "inspect_state": ToolDefinition(
                name="inspect_state",
                description="Inspect a persisted value from the configured memory backend.",
                input_schema=INSPECT_STATE_SCHEMA,
                handler=self._handle_inspect_state,
            ),
            "handoff": ToolDefinition(
                name="handoff",
                description="Record a task handoff between agents and persist the transition.",
                input_schema=HANDOFF_SCHEMA,
                handler=self._handle_handoff,
            ),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-style tool metadata with JSON Schemas."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a tool by name with JSON-decoded arguments."""
        if name not in self._tools:
            raise ValueError(f"unknown tool: {name}")
        payload = arguments or {}
        if not isinstance(payload, dict):
            raise TypeError("tool arguments must be an object")
        return self._tools[name].handler(payload)

    def _handle_run_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = str(payload["template"])
        variables = payload.get("vars", {})
        context = payload.get("context", {})
        if not isinstance(variables, dict) or not isinstance(context, dict):
            raise TypeError("vars and context must be objects")

        namespace = str(context.get("namespace", f"mcp:{template}"))
        rendered_vars = {str(k): str(v) for k, v in variables.items()}
        summary, results = self.adhoc_orchestrator.run_template(
            template,
            namespace=namespace,
            variables=rendered_vars,
            base_context=context,
        )
        return {
            "summary": summary.__dict__,
            "steps": [
                {
                    "step_id": item.step.id,
                    "title": item.step.title,
                    "action_type": item.step.action_type,
                    "status": item.status,
                    "effect": item.decision.effect.value,
                    "rule": item.decision.matched_rule_id,
                    "reason": item.decision.reason,
                }
                for item in results
            ],
        }

    def _handle_inspect_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        namespace = str(payload["namespace"])
        key = str(payload["key"])
        return {
            "namespace": namespace,
            "key": key,
            "value": self.memory.get(namespace, key),
            "known_keys": self.memory.keys(namespace),
        }

    def _handle_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        from_agent = str(payload["from_agent"])
        to_agent = str(payload["to_agent"])
        task_id = str(payload["task_id"])
        reason = str(payload["reason"])

        run = self.fixed_orchestrator.run(
            workflow_name=f"handoff:{task_id}",
            payload={
                "action_type": "write",
                "from_agent": from_agent,
                "to_agent": to_agent,
                "task_id": task_id,
                "reason": reason,
            },
        )
        record = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "task_id": task_id,
            "reason": reason,
            "run_id": run.run_id,
            "status": run.status,
        }
        self.memory.set(f"handoff:{task_id}", "latest", record)
        return record
