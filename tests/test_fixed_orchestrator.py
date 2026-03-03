"""Tests for deterministic fixed orchestrator runtime."""

from antigravity_orchestrator.runtime import FixedOrchestrator


def test_run_allows_default_read_and_persists_result() -> None:
    orchestrator = FixedOrchestrator()

    result = orchestrator.run("wf", {"action_type": "read"})

    assert result.status == "completed"
    saved = orchestrator.memory_backend.get("wf", result.run_id)
    assert saved["status"] == "completed"


def test_run_blocks_delete_in_production() -> None:
    orchestrator = FixedOrchestrator()

    result = orchestrator.run(
        "wf",
        {"action_type": "delete", "environment": "production"},
    )

    assert result.status == "blocked"
    assert result.output["matched_rule_id"] == "block-delete-production"


def test_custom_action_handler_is_used() -> None:
    orchestrator = FixedOrchestrator()

    orchestrator.register_action("alert", lambda payload: {"ok": payload.get("service")})
    result = orchestrator.run("wf", {"action_type": "alert", "service": "payments"})

    assert result.output == {"ok": "payments"}
