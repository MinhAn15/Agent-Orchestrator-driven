"""Example incident triage workflow using multiple connectors."""

from __future__ import annotations

import json
from pathlib import Path

from connectors.base import ConnectorContext
from connectors.filesystem_connector import FilesystemConnector
from connectors.github_connector import GitHubConnector
from connectors.registry import ConnectorRegistry


def run() -> dict:
    registry = ConnectorRegistry()
    workspace = Path(__file__).parent

    fs = FilesystemConnector(root_dir=str(workspace), read_only=False)
    gh = GitHubConnector(read_only=True)

    registry.register(fs, version="v1")
    registry.register(gh, version="v1")

    context = ConnectorContext(request_id="incident-001", actor="triage-bot")

    incident = registry.get("filesystem").invoke(
        {"action": "read", "path": "sample_incident.json"},
        context,
    )
    incident_payload = json.loads(incident["content"])

    issue_metadata = registry.get("github").invoke(
        {
            "operation": "get_issue",
            "owner": incident_payload["repo_owner"],
            "repo": incident_payload["repo_name"],
            "issue_number": incident_payload["linked_issue"],
        },
        context,
    )

    summary = {
        "incident_id": incident_payload["incident_id"],
        "severity": incident_payload["severity"],
        "title": incident_payload["title"],
        "github_issue_title": issue_metadata["data"].get("title"),
        "github_issue_state": issue_metadata["data"].get("state"),
    }

    registry.get("filesystem").invoke(
        {
            "action": "write",
            "path": "triage_summary.json",
            "content": json.dumps(summary, indent=2),
        },
        context,
    )

    return {
        "summary": summary,
        "capability_discovery": registry.discover_by_capability("github:issue:read"),
    }


if __name__ == "__main__":
    output = run()
    print(json.dumps(output, indent=2))
