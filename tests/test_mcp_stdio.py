"""Integration tests for MCP stdio JSON-RPC endpoint."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def _run_rpc_lines(lines: list[str]) -> list[dict[str, object]]:
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.Popen(
        [sys.executable, "-m", "antigravity.cli", "mcp", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=repo_root,
        env=env,
    )

    payload = "\n".join(lines) + "\n"
    stdout, stderr = proc.communicate(payload, timeout=10)
    assert proc.returncode == 0, stderr

    return [json.loads(line) for line in stdout.splitlines() if line.strip()]


def test_mcp_stdio_list_and_call_workflow() -> None:
    responses = _run_rpc_lines(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "run_workflow",
                        "arguments": {
                            "template": "incident-response",
                            "vars": {"team": "SRE", "service": "billing", "severity": "P2"},
                            "context": {"namespace": "mcp-test-ns", "environment": "staging"},
                        },
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "inspect_state",
                    "params": {"namespace": "mcp-test-ns", "key": "summary"},
                }
            ),
        ]
    )

    assert responses[0]["id"] == 1
    assert responses[0]["jsonrpc"] == "2.0"
    tool_names = {item["name"] for item in responses[0]["result"]["tools"]}
    assert {"run_workflow", "inspect_state", "handoff"}.issubset(tool_names)

    assert responses[1]["id"] == 2
    assert responses[1]["result"]["summary"]["namespace"] == "mcp-test-ns"
    assert isinstance(responses[1]["result"]["steps"], list)

    assert responses[2]["id"] == 3
    assert responses[2]["result"]["namespace"] == "mcp-test-ns"
    assert responses[2]["result"]["key"] == "summary"
    assert isinstance(responses[2]["result"]["value"], dict)


def test_mcp_stdio_returns_structured_errors() -> None:
    responses = _run_rpc_lines(
        [
            "{not-json}",
            json.dumps({"jsonrpc": "2.0", "id": 9, "method": "missing", "params": {}}),
        ]
    )

    assert responses[0]["error"]["code"] == -32700
    assert responses[0]["id"] is None
    assert responses[1]["id"] == 9
    assert responses[1]["error"]["code"] == -32601
