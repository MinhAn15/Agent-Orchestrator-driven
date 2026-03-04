"""MCP tool handlers for Antigravity."""

from __future__ import annotations

from typing import Any

from antigravity.handoff import HandoffBus, HandoffToken


def handle_handoff_transfer(arguments: dict[str, Any], handoff_bus: HandoffBus) -> dict[str, Any]:
    """Handle MCP handoff transfer requests."""
    token = HandoffToken(
        from_agent=str(arguments["from_agent"]),
        to_agent=str(arguments["to_agent"]),
        task_id=str(arguments["task_id"]),
        context_snapshot=dict(arguments["context_snapshot"]),
        reason=str(arguments["reason"]),
    )
    handoff_bus.transfer(token)
    return {"status": "transferred", "task_id": token.task_id, "to_agent": token.to_agent}
