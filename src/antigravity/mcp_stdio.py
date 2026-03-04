"""JSON-RPC 2.0 stdio loop for MCP-style tooling."""

from __future__ import annotations

import json
import logging
import sys

from antigravity.mcp_tools import MCPToolRegistry

LOGGER = logging.getLogger(__name__)


class JsonRpcError(Exception):
    """Structured JSON-RPC error wrapper."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def run_stdio_loop(registry: MCPToolRegistry | None = None) -> int:
    """Handle newline-delimited JSON-RPC requests from stdin."""
    tools = registry or MCPToolRegistry()
    logging.basicConfig(level=logging.INFO)

    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            _emit({"jsonrpc": "2.0", "id": None, "error": _error(-32700, "Parse error")})
            continue

        response = _handle_request(tools, request)
        if response is not None:
            _emit(response)
    return 0


def _handle_request(registry: MCPToolRegistry, request: object) -> dict[str, object] | None:
    request_id = None
    try:
        if not isinstance(request, dict):
            raise JsonRpcError(-32600, "Invalid Request")
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0":
            raise JsonRpcError(-32600, "Invalid Request")

        method = request.get("method")
        if not isinstance(method, str):
            raise JsonRpcError(-32600, "Invalid Request")

        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise JsonRpcError(-32602, "Invalid params")

        result = _dispatch(registry, method, params)
        if "id" not in request:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except JsonRpcError as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": _error(exc.code, exc.message)}
    except Exception as exc:  # pragma: no cover - defensive catch for long-running stdio server
        LOGGER.exception("Unhandled request failure")
        return {"jsonrpc": "2.0", "id": request_id, "error": _error(-32000, f"Server error: {exc}")}


def _dispatch(registry: MCPToolRegistry, method: str, params: dict[str, object]) -> object:
    if method in {"tools/list", "mcp.tools.list"}:
        return {"tools": registry.list_tools()}

    if method in {"tools/call", "mcp.tools.call"}:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            raise JsonRpcError(-32602, "Invalid params: missing tool name")
        if not isinstance(arguments, dict):
            raise JsonRpcError(-32602, "Invalid params: arguments must be an object")
        return registry.call_tool(name, arguments)

    if method in {"run_workflow", "inspect_state", "handoff"}:
        return registry.call_tool(method, params)

    raise JsonRpcError(-32601, f"Method not found: {method}")


def _emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _error(code: int, message: str) -> dict[str, object]:
    return {"code": code, "message": message}
