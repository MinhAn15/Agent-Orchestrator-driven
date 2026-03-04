"""Tests for handoff transfer semantics and orchestration integration."""

from antigravity.handoff import HandoffBus, HandoffToken
from antigravity.memory import InMemoryBackend
from antigravity.mcp_tools import handle_handoff_transfer
from antigravity_orchestrator.runtime import FixedOrchestrator


def test_handoff_bus_transfer_and_receive_fifo() -> None:
    bus = HandoffBus(InMemoryBackend())
    first = HandoffToken(
        from_agent="planner",
        to_agent="approver",
        task_id="t-1",
        context_snapshot={"a": 1},
        reason="approval needed",
    )
    second = HandoffToken(
        from_agent="planner",
        to_agent="approver",
        task_id="t-2",
        context_snapshot={"b": 2},
        reason="second",
    )

    bus.transfer(first)
    bus.transfer(second)

    received_first = bus.receive("approver")
    received_second = bus.receive("approver")

    assert received_first is not None
    assert received_second is not None
    assert received_first.task_id == "t-1"
    assert received_second.task_id == "t-2"
    assert bus.receive("approver") is None


def test_context_snapshot_is_exact_at_transfer_time() -> None:
    backend = InMemoryBackend()
    bus = HandoffBus(backend)
    snapshot = {"task": "approve", "nested": {"priority": "high"}}

    token = HandoffToken(
        from_agent="planner",
        to_agent="human-review",
        task_id="task-99",
        context_snapshot=snapshot.copy(),
        reason="requires sign-off",
    )

    bus.transfer(token)
    snapshot["task"] = "mutated"
    snapshot["nested"]["priority"] = "low"

    received = bus.receive("human-review")

    assert received is not None
    assert received.context_snapshot == {"task": "approve", "nested": {"priority": "high"}}


def test_fixed_orchestrator_emits_and_persists_handoff_when_escalating() -> None:
    backend = InMemoryBackend()
    bus = HandoffBus(backend)
    orchestrator = FixedOrchestrator(memory_backend=backend, handoff_bus=bus)
    payload = {
        "action_type": "write",
        "domain": "financial",
        "task_id": "task-fin-1",
        "escalate_to_agent": "human-approver",
        "agent_id": "payments-agent",
    }

    result = orchestrator.run("wf", payload)

    assert result.status == "requires_approval"
    handoff = result.output["handoff"]
    assert handoff["to_agent"] == "human-approver"
    saved_handoff_keys = [key for key in backend.keys("wf") if key.endswith(":handoff")]
    assert len(saved_handoff_keys) == 1
    assert backend.get("wf", saved_handoff_keys[0])["task_id"] == "task-fin-1"


def test_mcp_handoff_tool_uses_bus_transfer() -> None:
    bus = HandoffBus(InMemoryBackend())

    response = handle_handoff_transfer(
        {
            "from_agent": "agent-a",
            "to_agent": "agent-b",
            "task_id": "task-1",
            "context_snapshot": {"ticket": 42},
            "reason": "escalation",
        },
        bus,
    )

    assert response == {"status": "transferred", "task_id": "task-1", "to_agent": "agent-b"}
    assert bus.receive("agent-b") is not None
