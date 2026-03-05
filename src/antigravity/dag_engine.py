"""DAG workflow engine for YAML-based orchestration templates."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from antigravity.memory import InMemoryBackend, MemoryBackend
from connectors.base import BaseConnector, ConnectorContext
from connectors.registry import ConnectorRegistry, resolve_skill

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class DagNode:
    id: str
    skill: str
    input: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    condition: str | bool | None = None


@dataclass(frozen=True)
class DagSpec:
    workflow_id: str
    vars: dict[str, Any]
    nodes: list[DagNode]


@dataclass(frozen=True)
class DagNodeResult:
    node_id: str
    status: str
    output: dict[str, Any]


@dataclass(frozen=True)
class DagRunResult:
    workflow_id: str
    node_results: list[DagNodeResult]


class DagEngine:
    """Execute YAML DAG specs with dependency and parallel scheduling."""

    def __init__(self, registry: ConnectorRegistry, memory: MemoryBackend | None = None) -> None:
        self.registry = registry
        self.memory = memory or InMemoryBackend()

    def run_template(self, template: str | Path, *, variables: Mapping[str, Any] | None = None) -> DagRunResult:
        spec = load_dag_spec(template, variables=variables)
        return asyncio.run(self.run_spec(spec))

    async def run_spec(self, spec: DagSpec) -> DagRunResult:
        nodes_by_id = {node.id: node for node in spec.nodes}
        _validate_graph(nodes_by_id)

        pending = set(nodes_by_id)
        completed: set[str] = set()
        results: dict[str, DagNodeResult] = {}

        while pending:
            ready = [
                nodes_by_id[node_id]
                for node_id in sorted(pending)
                if all(dep in completed for dep in nodes_by_id[node_id].depends_on)
            ]
            if not ready:
                raise ValueError("No executable DAG nodes found; check for cycles or invalid dependencies")

            batch_results = await asyncio.gather(
                *(self._execute_node(node, spec=spec, prior_results=results) for node in ready)
            )
            for node_result in batch_results:
                results[node_result.node_id] = node_result
                completed.add(node_result.node_id)
                pending.remove(node_result.node_id)

        ordered = [results[node.id] for node in spec.nodes]
        return DagRunResult(workflow_id=spec.workflow_id, node_results=ordered)

    async def _execute_node(
        self,
        node: DagNode,
        *,
        spec: DagSpec,
        prior_results: Mapping[str, DagNodeResult],
    ) -> DagNodeResult:
        if not _condition_matches(node.condition, spec.vars, prior_results):
            result = DagNodeResult(node_id=node.id, status="skipped", output={"reason": "condition_false"})
            self.memory.set(spec.workflow_id, node.id, {"status": result.status, "output": result.output})
            return result

        connector = self._resolve_skill(node.skill)
        payload = _render_payload(node.input, spec.vars)
        context = ConnectorContext(request_id=f"{spec.workflow_id}:{node.id}")
        output = await asyncio.to_thread(connector.invoke, payload, context)

        result = DagNodeResult(node_id=node.id, status="completed", output=dict(output))
        self.memory.set(spec.workflow_id, node.id, {"status": result.status, "output": result.output})
        return result

    def _resolve_skill(self, skill_name: str) -> BaseConnector:
        return resolve_skill(self.registry, skill_name)


def load_dag_spec(template: str | Path, *, variables: Mapping[str, Any] | None = None) -> DagSpec:
    path = Path(template)
    raw = _load_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("DAG template must be a YAML mapping")

    defaults = raw.get("vars") or {}
    if not isinstance(defaults, dict):
        raise ValueError("DAG vars must be a mapping")
    merged_vars = {**defaults, **dict(variables or {})}

    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list):
        raise ValueError("DAG template requires a 'nodes' list")

    nodes: list[DagNode] = []
    for idx, raw_node in enumerate(raw_nodes, start=1):
        if not isinstance(raw_node, dict):
            raise ValueError(f"node {idx} must be a mapping")
        node_id = str(raw_node.get("id") or idx)
        skill = raw_node.get("skill")
        if not isinstance(skill, str) or not skill:
            raise ValueError(f"node '{node_id}' missing required skill")
        nodes.append(
            DagNode(
                id=node_id,
                skill=skill,
                input=dict(raw_node.get("input") or {}),
                depends_on=[str(dep) for dep in (raw_node.get("depends_on") or [])],
                parallel_with=[str(dep) for dep in (raw_node.get("parallel_with") or [])],
                condition=raw_node.get("condition"),
            )
        )

    workflow_id = str(raw.get("workflow_id") or path.stem)
    return DagSpec(workflow_id=workflow_id, vars=merged_vars, nodes=nodes)


def _validate_graph(nodes_by_id: Mapping[str, DagNode]) -> None:
    for node in nodes_by_id.values():
        for dep in node.depends_on:
            if dep not in nodes_by_id:
                raise ValueError(f"node '{node.id}' depends on unknown node '{dep}'")


def _condition_matches(
    condition: str | bool | None,
    variables: Mapping[str, Any],
    prior_results: Mapping[str, DagNodeResult],
) -> bool:
    if condition is None:
        return True
    if isinstance(condition, bool):
        return condition
    if not isinstance(condition, str):
        return False

    eval_globals = {"__builtins__": {}}
    eval_locals = {
        "vars": dict(variables),
        "results": {node_id: result.output for node_id, result in prior_results.items()},
    }
    return bool(eval(condition, eval_globals, eval_locals))


def _render_payload(payload: Mapping[str, Any], variables: Mapping[str, Any]) -> dict[str, Any]:
    rendered: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            rendered[key] = value.format(**variables)
        elif isinstance(value, dict):
            rendered[key] = _render_payload(value, variables)
        else:
            rendered[key] = value
    return rendered


def _load_yaml(raw: str) -> Any:
    if yaml is not None:
        return yaml.safe_load(raw)
    return _parse_simple_yaml(raw)


def _parse_simple_yaml(raw: str) -> Any:
    lines = [line.rstrip("\n") for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")]

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        stripped = lines[index].lstrip()
        is_list = stripped.startswith("- ")
        container: Any = [] if is_list else {}

        while index < len(lines):
            line = lines[index]
            current_indent = len(line) - len(line.lstrip(" "))
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ValueError(f"Invalid indentation near: {line}")
            content = line.strip()

            if isinstance(container, list):
                if not content.startswith("- "):
                    break
                item_content = content[2:].strip()
                if not item_content:
                    item, index = parse_block(index + 1, indent + 2)
                    container.append(item)
                    continue
                if ":" in item_content:
                    key, value = item_content.split(":", 1)
                    item: dict[str, Any] = {key.strip(): _parse_scalar(value.strip())}
                    index += 1
                    while index < len(lines):
                        next_line = lines[index]
                        next_indent = len(next_line) - len(next_line.lstrip(" "))
                        if next_indent <= indent:
                            break
                        if next_indent != indent + 2:
                            raise ValueError(f"Invalid indentation near: {next_line}")
                        k, v = next_line.strip().split(":", 1)
                        if v.strip():
                            item[k.strip()] = _parse_scalar(v.strip())
                            index += 1
                        else:
                            nested, index = parse_block(index + 1, indent + 4)
                            item[k.strip()] = nested
                    container.append(item)
                    continue
                container.append(_parse_scalar(item_content))
                index += 1
                continue

            key, value = content.split(":", 1)
            key = key.strip()
            if value.strip():
                container[key] = _parse_scalar(value.strip())
                index += 1
            else:
                nested, index = parse_block(index + 1, indent + 2)
                container[key] = nested
        return container, index

    parsed, _ = parse_block(0, 0)
    return parsed


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()
        if not inner:
            return {}
        result: dict[str, Any] = {}
        for part in inner.split(","):
            key, raw_val = part.split(":", 1)
            result[key.strip()] = _parse_scalar(raw_val.strip())
        return result
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
