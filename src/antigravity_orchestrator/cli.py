"""Command-line interface for antigravity orchestrator."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from antigravity_orchestrator.models import ExecutionResult
from antigravity_orchestrator.runtime import FixedOrchestrator


def run_workflow(workflow_name: str, payload: dict[str, object]) -> ExecutionResult:
    """Minimal API entrypoint for running a workflow."""
    orchestrator = FixedOrchestrator()
    return orchestrator.run(workflow_name=workflow_name, payload=payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antigravity")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a workflow")
    run_parser.add_argument("workflow_name", help="Workflow name to execute")
    run_parser.add_argument(
        "--payload",
        default="{}",
        help="JSON payload passed to the workflow",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        payload = json.loads(args.payload)
        result = run_workflow(args.workflow_name, payload)
        print(json.dumps(asdict(result), default=str, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
