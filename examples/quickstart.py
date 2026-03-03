"""Quickstart example for deterministic Antigravity orchestration."""

from __future__ import annotations

from antigravity_orchestrator.runtime import FixedOrchestrator


def send_alert(payload: dict[str, object]) -> dict[str, object]:
    return {
        "message": "Incident alert sent.",
        "severity": payload.get("severity", "info"),
        "service": payload.get("service", "unknown"),
    }


if __name__ == "__main__":
    orchestrator = FixedOrchestrator()
    orchestrator.register_action("alert", send_alert)

    result = orchestrator.run(
        workflow_name="incident-response",
        payload={
            "action_type": "alert",
            "severity": "high",
            "service": "billing-api",
            "environment": "production",
        },
    )
    print(result)
