"""Command-line interface for antigravity orchestrator."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from uuid import uuid4

from antigravity_orchestrator.models import ExecutionResult


def run_workflow(workflow_name: str, payload: dict[str, object]) -> ExecutionResult:
    """Minimal API entrypoint for running a workflow."""
    return ExecutionResult(
        run_id=str(uuid4()),
        status="completed",
        output={
            "workflow": workflow_name,
            "inputs": payload,
            "message": f"Workflow '{workflow_name}' completed in scaffold runtime.",
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="antigravity-orchestrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-workflow", help="Run a workflow")
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

    if args.command == "run-workflow":
        payload = json.loads(args.payload)
        result = run_workflow(args.workflow_name, payload)
        print(json.dumps(asdict(result), default=str, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
