"""CLI entrypoint for running ad-hoc orchestration workflows."""

from __future__ import annotations

import argparse
import json
from uuid import uuid4

from antigravity.adhoc import AdHocOrchestrator


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
