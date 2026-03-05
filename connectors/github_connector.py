"""GitHub connector focused on issue/PR metadata access."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib import error, request

from connectors.base import BaseConnector, ConnectorContext, ConnectorError


class GitHubConnector(BaseConnector):
    name = "github"
    capabilities = ("github:issue:read", "github:pr:read", "github:repo:read")
    write_operations = {"create_issue", "add_label", "post_comment", "create_pr", "update_issue", "update_pr"}

    def __init__(self, token: str | None = None, read_only: bool = True, timeout: int = 10) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.read_only = read_only
        self.timeout = timeout

    def invoke(self, input: Mapping[str, Any], context: ConnectorContext) -> Mapping[str, Any]:
        operation = input.get("operation")
        owner = input.get("owner")
        repo = input.get("repo")

        if self.read_only and operation in self.write_operations:
            raise ConnectorError("READ_ONLY", "GitHub connector is read-only by default")

        if not owner or not repo:
            raise ConnectorError("INVALID_INPUT", "'owner' and 'repo' are required")

        payload: Mapping[str, Any] | None = None
        method = "GET"

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
        elif operation == "create_issue":
            title = input.get("title")
            if not title:
                raise ConnectorError("INVALID_INPUT", "'title' is required for create_issue")
            path = f"/repos/{owner}/{repo}/issues"
            method = "POST"
            payload = {
                "title": title,
                "body": input.get("body"),
                "labels": input.get("labels"),
                "assignees": input.get("assignees"),
            }
        elif operation == "add_label":
            issue_number = input.get("issue_number")
            labels = input.get("labels")
            if not issue_number:
                raise ConnectorError("INVALID_INPUT", "'issue_number' is required for add_label")
            if not labels:
                raise ConnectorError("INVALID_INPUT", "'labels' is required for add_label")
            path = f"/repos/{owner}/{repo}/issues/{issue_number}/labels"
            method = "POST"
            payload = {"labels": labels if isinstance(labels, list) else [labels]}
        elif operation == "post_comment":
            issue_number = input.get("issue_number")
            body = input.get("body")
            if not issue_number:
                raise ConnectorError("INVALID_INPUT", "'issue_number' is required for post_comment")
            if not body:
                raise ConnectorError("INVALID_INPUT", "'body' is required for post_comment")
            path = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
            method = "POST"
            payload = {"body": body}
        elif operation == "create_pr":
            title = input.get("title")
            head = input.get("head")
            base = input.get("base")
            if not title or not head or not base:
                raise ConnectorError("INVALID_INPUT", "'title', 'head', and 'base' are required for create_pr")
            path = f"/repos/{owner}/{repo}/pulls"
            method = "POST"
            payload = {
                "title": title,
                "head": head,
                "base": base,
                "body": input.get("body"),
                "draft": bool(input.get("draft", False)),
            }
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

        body = json.dumps({k: v for k, v in (payload or {}).items() if v is not None}).encode("utf-8") if payload is not None else None
        req = request.Request(url=url, method=method, headers=headers, data=body)

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return {
                    "status": response.status,
                    "operation": operation,
                    "method": method,
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
