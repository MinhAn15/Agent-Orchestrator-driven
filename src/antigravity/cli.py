"""CLI entrypoint for running ad-hoc orchestration workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from antigravity.adhoc import AdHocOrchestrator
from antigravity.dag_engine import DagEngine
from antigravity.mcp_stdio import run_stdio_loop
from connectors.github_connector import GitHubConnector
from connectors.http_connector import HTTPConnector
from connectors.registry import ConnectorRegistry


def _json_object(raw: str) -> dict[str, str]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return {str(k): str(v) for k, v in data.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antigravity", description="Ad-hoc agent orchestration CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a workflow template")
    run_parser.add_argument("template", help="Template slug, e.g. incident-response")
    run_parser.add_argument("--namespace", default=f"run-{uuid4()}", help="Memory namespace")
    run_parser.add_argument(
        "--vars",
        default="{}",
        type=_json_object,
        help="Template variables as JSON object",
    )
    run_parser.add_argument(
        "--context",
        default="{}",
        type=_json_object,
        help="Policy context as JSON object (environment, domain, data_classification, ...)",
    )

    mcp_parser = sub.add_parser("mcp", help="Run MCP-compatible stdio JSON-RPC server")
    mcp_parser.add_argument("--stdio", action="store_true", help="Enable stdio transport")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        template_path = Path(args.template)
        if template_path.suffix.lower() in {".yaml", ".yml"}:
            registry = ConnectorRegistry()
            registry.register(HTTPConnector())
            registry.register(GitHubConnector())
            engine = DagEngine(registry=registry)
            dag_result = engine.run_template(template_path, variables=args.vars)
            print(json.dumps({
                "workflow_id": dag_result.workflow_id,
                "namespace": dag_result.workflow_id,
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "status": node.status,
                        "output": node.output,
                    }
                    for node in dag_result.node_results
                ],
            }, indent=2))
            return 0

        orchestrator = AdHocOrchestrator()
        summary, results = orchestrator.run_template(
            args.template,
            namespace=args.namespace,
            variables=args.vars,
            base_context=args.context,
        )
        print(json.dumps({
            "summary": summary.__dict__,
            "steps": [
                {
                    "step_id": result.step.id,
                    "title": result.step.title,
                    "action_type": result.step.action_type,
                    "status": result.status,
                    "effect": result.decision.effect.value,
                    "rule": result.decision.matched_rule_id,
                    "reason": result.decision.reason,
                }
                for result in results
            ],
        }, indent=2))
        return 0

    if args.command == "mcp":
        if args.stdio:
            return run_stdio_loop()
        parser.error("mcp currently requires --stdio")

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
