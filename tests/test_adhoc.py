"""Tests for ad-hoc orchestration runtime."""

from antigravity.adhoc import AdHocOrchestrator, infer_action_type, parse_markdown_steps


def test_parse_markdown_steps_extracts_checklist_items() -> None:
    markdown = """
# Demo
## Workflow
- [ ] Investigate incident context
- [x] Delete stale table
Normal line
- [ ] Notify external vendor
"""
    steps = parse_markdown_steps(markdown)

    assert [s.id for s in steps] == ["01", "02", "03"]
    assert [s.action_type for s in steps] == ["read", "delete", "send_external"]


def test_infer_action_type_maps_keywords() -> None:
    assert infer_action_type("Delete row") == "delete"
    assert infer_action_type("Notify external partner") == "send_external"
    assert infer_action_type("Update ticket") == "write"
    assert infer_action_type("Inspect logs") == "read"


def test_orchestrator_applies_default_policy_and_persists_summary() -> None:
    orchestrator = AdHocOrchestrator()

    summary, results = orchestrator.run_template(
        "incident-response",
        namespace="tests-adhoc",
        variables={"team": "SRE", "service": "payments", "severity": "P1"},
        base_context={"environment": "production", "data_classification": "confidential"},
    )

    assert summary.total_steps > 0
    assert summary.denied >= 0
    assert len(results) == summary.total_steps
    assert orchestrator.memory.get("tests-adhoc", "summary")["workflow_slug"] == "incident-response"
