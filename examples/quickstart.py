"""Quickstart demo: run an ad-hoc incident workflow in one command."""

from __future__ import annotations

import json

from antigravity.adhoc import AdHocOrchestrator


def main() -> None:
    orchestrator = AdHocOrchestrator()
    summary, results = orchestrator.run_template(
        "incident-response",
        namespace="quickstart",
        variables={
            "team": "Platform",
            "severity": "P1",
            "service": "payments-api",
        },
        base_context={
            "environment": "production",
            "data_classification": "confidential",
        },
    )

    print("=== Antigravity Quickstart ===")
    print(json.dumps(summary.__dict__, indent=2))
    print("\nStep outcomes:")
    for result in results:
        print(f"- [{result.status}] {result.step.title} ({result.step.action_type})")


if __name__ == "__main__":
    main()
