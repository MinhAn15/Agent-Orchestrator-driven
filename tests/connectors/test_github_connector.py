"""Tests for GitHubConnector."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from urllib import error

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from connectors.base import ConnectorContext, ConnectorError
from connectors.github_connector import GitHubConnector


class DummyResponse:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def context() -> ConnectorContext:
    return ConnectorContext(request_id="req-123")


def test_read_only_rejects_write_operations(context: ConnectorContext) -> None:
    connector = GitHubConnector(read_only=True)

    with pytest.raises(ConnectorError, match="read-only") as exc:
        connector.invoke(
            {
                "operation": "create_issue",
                "owner": "acme",
                "repo": "demo",
                "title": "Bug",
            },
            context,
        )

    assert exc.value.code == "READ_ONLY"


def test_uses_env_token_when_not_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    connector = GitHubConnector()

    assert connector.token == "env-token"


def test_explicit_token_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    connector = GitHubConnector(token="explicit-token")

    assert connector.token == "explicit-token"


def test_get_issue_uses_get(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        return DummyResponse(200, {"id": 1})

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t", read_only=True)
    result = connector.invoke({"operation": "get_issue", "owner": "acme", "repo": "demo", "issue_number": 1}, context)

    assert result["status"] == 200
    assert result["method"] == "GET"
    assert captured["method"] == "GET"
    assert captured["url"].endswith("/repos/acme/demo/issues/1")


def test_create_issue_posts_payload(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return DummyResponse(201, {"number": 42})

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t", read_only=False)
    result = connector.invoke(
        {
            "operation": "create_issue",
            "owner": "acme",
            "repo": "demo",
            "title": "Bug report",
            "body": "Steps",
            "labels": ["bug"],
        },
        context,
    )

    assert result["status"] == 201
    assert result["method"] == "POST"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/repos/acme/demo/issues")
    assert captured["body"]["title"] == "Bug report"


def test_add_label_accepts_string_label(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return DummyResponse(200, {"ok": True})

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t", read_only=False)
    connector.invoke(
        {
            "operation": "add_label",
            "owner": "acme",
            "repo": "demo",
            "issue_number": 1,
            "labels": "bug",
        },
        context,
    )

    assert captured["body"] == {"labels": ["bug"]}




def test_post_comment_posts_payload(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return DummyResponse(201, {"id": 1001})

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t", read_only=False)
    result = connector.invoke(
        {
            "operation": "post_comment",
            "owner": "acme",
            "repo": "demo",
            "issue_number": 5,
            "body": "Investigating now",
        },
        context,
    )

    assert result["status"] == 201
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/repos/acme/demo/issues/5/comments")
    assert captured["body"] == {"body": "Investigating now"}


def test_create_pr_posts_payload(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    captured = {}

    def fake_urlopen(req, timeout):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return DummyResponse(201, {"number": 11})

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t", read_only=False)
    result = connector.invoke(
        {
            "operation": "create_pr",
            "owner": "acme",
            "repo": "demo",
            "title": "Ship fix",
            "head": "fix-branch",
            "base": "main",
            "body": "Details",
            "draft": True,
        },
        context,
    )

    assert result["status"] == 201
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/repos/acme/demo/pulls")
    assert captured["body"]["head"] == "fix-branch"
    assert captured["body"]["draft"] is True


def test_post_comment_requires_body(context: ConnectorContext) -> None:
    connector = GitHubConnector(token="t", read_only=False)

    with pytest.raises(ConnectorError) as exc:
        connector.invoke(
            {
                "operation": "post_comment",
                "owner": "acme",
                "repo": "demo",
                "issue_number": 1,
            },
            context,
        )

    assert exc.value.code == "INVALID_INPUT"


def test_create_pr_requires_required_fields(context: ConnectorContext) -> None:
    connector = GitHubConnector(token="t", read_only=False)

    with pytest.raises(ConnectorError) as exc:
        connector.invoke(
            {
                "operation": "create_pr",
                "owner": "acme",
                "repo": "demo",
                "title": "PR",
                "base": "main",
            },
            context,
        )

    assert exc.value.code == "INVALID_INPUT"


def test_http_error_is_normalized(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    def fake_urlopen(req, timeout):
        raise error.HTTPError(req.full_url, 403, "forbidden", hdrs=None, fp=io.BytesIO(b"{}"))

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t")
    with pytest.raises(ConnectorError) as exc:
        connector.invoke({"operation": "get_pr", "owner": "acme", "repo": "demo", "pr_number": 7}, context)

    assert exc.value.code == "HTTP_ERROR"


def test_network_error_is_normalized(monkeypatch: pytest.MonkeyPatch, context: ConnectorContext) -> None:
    def fake_urlopen(req, timeout):
        raise error.URLError("down")

    monkeypatch.setattr("connectors.github_connector.request.urlopen", fake_urlopen)

    connector = GitHubConnector(token="t")
    with pytest.raises(ConnectorError) as exc:
        connector.invoke({"operation": "list_open_issues", "owner": "acme", "repo": "demo"}, context)

    assert exc.value.code == "NETWORK_ERROR"
