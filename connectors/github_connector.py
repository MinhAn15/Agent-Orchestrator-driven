"""GitHub connector focused on issue/PR metadata access."""

from __future__ import annotations

import json
from typing import Any, Mapping
from urllib import error, request

from connectors.base import BaseConnector, ConnectorContext, ConnectorError


class GitHubConnector(BaseConnector):
    name = "github"
    capabilities = ("github:issue:read", "github:pr:read", "github:repo:read")

    def __init__(self, token: str | None = None, read_only: bool = True, timeout: int = 10) -> None:
        self.token = token
        self.read_only = read_only
        self.timeout = timeout

    def invoke(self, input: Mapping[str, Any], context: ConnectorContext) -> Mapping[str, Any]:
        operation = input.get("operation")
        owner = input.get("owner")
        repo = input.get("repo")

        if self.read_only and operation in {"create_issue", "create_pr", "update_issue", "update_pr"}:
            raise ConnectorError("READ_ONLY", "GitHub connector is read-only by default")

        if not owner or not repo:
            raise ConnectorError("INVALID_INPUT", "'owner' and 'repo' are required")

        if operation == "get_issue":
            issue_number = input.get("issue_number")
            if not issue_number:
                raise ConnectorError("INVALID_INPUT", "'issue_number' is required for get_issue")
            path = f"/repos/{owner}/{repo}/issues/{issue_number}"
        elif operation == "get_pr":
            pr_number = input.get("pr_number")
            if not pr_number:
                raise ConnectorError("INVALID_INPUT", "'pr_number' is required for get_pr")
            path = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        elif operation == "list_open_issues":
            path = f"/repos/{owner}/{repo}/issues?state=open"
        else:
            raise ConnectorError("INVALID_INPUT", f"Unsupported operation: {operation}")

        url = f"https://api.github.com{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "X-Request-Id": context.request_id,
            "User-Agent": "antigravity-github-connector",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = request.Request(url=url, method="GET", headers=headers)

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return {
                    "status": response.status,
                    "operation": operation,
                    "data": payload,
                }
        except error.HTTPError as exc:
            raise ConnectorError(
                "HTTP_ERROR",
                f"GitHub API request failed with {exc.code}",
                {"status": exc.code, "url": url},
            ) from exc
        except error.URLError as exc:
            raise ConnectorError(
                "NETWORK_ERROR",
                f"GitHub API request failed: {exc.reason}",
                {"url": url},
            ) from exc
