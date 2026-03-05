import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antigravity.dag_engine import DagEngine, load_dag_spec
from antigravity.memory import InMemoryBackend
from connectors.base import BaseConnector, ConnectorContext
from connectors.registry import ConnectorRegistry


class RecordingConnector(BaseConnector):
    name = "recording"

    def __init__(self, events: list[tuple[str, str, float]]) -> None:
        self.events = events

    def invoke(self, input, context: ConnectorContext):
        node = str(input.get("node", "unknown"))
        delay = float(input.get("delay", 0.0))
        self.events.append(("start", node, time.perf_counter()))
        time.sleep(delay)
        self.events.append(("end", node, time.perf_counter()))
        return {"node": node, "request_id": context.request_id}


class EchoConnector(BaseConnector):
    name = "echo"

    def invoke(self, input, context: ConnectorContext):
        return {"input": dict(input), "request_id": context.request_id}


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "workflow.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_parallel_execution_ordering(tmp_path: Path) -> None:
    template = _write_yaml(
        tmp_path,
        """
workflow_id: wf-parallel
nodes:
  - id: a
    skill: recording
    input: {node: a, delay: 0.25}
  - id: b
    skill: recording
    input: {node: b, delay: 0.25}
  - id: c
    skill: recording
    depends_on: [a, b]
    input: {node: c, delay: 0.0}
""",
    )

    events: list[tuple[str, str, float]] = []
    registry = ConnectorRegistry()
    registry.register(RecordingConnector(events))
    memory = InMemoryBackend()
    engine = DagEngine(registry=registry, memory=memory)

    start = time.perf_counter()
    result = engine.run_template(template)
    elapsed = time.perf_counter() - start

    assert [node.node_id for node in result.node_results] == ["a", "b", "c"]
    assert elapsed < 0.45

    starts = {node: ts for kind, node, ts in events if kind == "start"}
    ends = {node: ts for kind, node, ts in events if kind == "end"}
    assert starts["c"] >= max(ends["a"], ends["b"])
    assert memory.get("wf-parallel", "a")["status"] == "completed"


def test_condition_skip_persists_to_memory(tmp_path: Path) -> None:
    template = _write_yaml(
        tmp_path,
        """
workflow_id: wf-condition
vars:
  should_run: false
nodes:
  - id: maybe
    skill: echo
    condition: vars.get("should_run", False)
    input: {msg: hello}
""",
    )

    registry = ConnectorRegistry()
    registry.register(EchoConnector())
    memory = InMemoryBackend()
    engine = DagEngine(registry=registry, memory=memory)

    result = engine.run_template(template)

    assert result.node_results[0].status == "skipped"
    assert memory.get("wf-condition", "maybe") == {
        "status": "skipped",
        "output": {"reason": "condition_false"},
    }


def test_depends_on_enforcement_and_validation(tmp_path: Path) -> None:
    template = _write_yaml(
        tmp_path,
        """
workflow_id: wf-deps
nodes:
  - id: first
    skill: echo
    input: {order: 1}
  - id: second
    skill: echo
    depends_on: [first]
    input: {order: 2}
""",
    )

    registry = ConnectorRegistry()
    registry.register(EchoConnector())
    memory = InMemoryBackend()
    engine = DagEngine(registry=registry, memory=memory)

    result = engine.run_template(template)
    assert [n.node_id for n in result.node_results] == ["first", "second"]
    assert memory.get("wf-deps", "second")["status"] == "completed"

    invalid = _write_yaml(
        tmp_path,
        """
workflow_id: wf-invalid
nodes:
  - id: only
    skill: echo
    depends_on: [missing]
""",
    )
    spec = load_dag_spec(invalid)
    with pytest.raises(ValueError, match="unknown node"):
        import asyncio
        asyncio.run(engine.run_spec(spec))
