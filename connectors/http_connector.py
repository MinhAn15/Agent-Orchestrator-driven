"""Generic REST connector."""

from __future__ import annotations

import json
from typing import Any, Mapping
from urllib import error, request

from connectors.base import BaseConnector, ConnectorContext, ConnectorError


class HTTPConnector(BaseConnector):
    name = "http"
    capabilities = ("http:get", "http:post", "http:put", "http:delete")

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def invoke(self, input: Mapping[str, Any], context: ConnectorContext) -> Mapping[str, Any]:
        method = str(input.get("method", "GET")).upper()
        url = input.get("url")
        headers = dict(input.get("headers", {}))
        payload = input.get("json")

        if not url:
            raise ConnectorError("INVALID_INPUT", "'url' is required")

        body: bytes | None = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")

        headers.setdefault("X-Request-Id", context.request_id)

        req = request.Request(url=url, method=method, headers=headers, data=body)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
                parsed: Any = raw
                if "application/json" in content_type and raw:
                    parsed = json.loads(raw)
                return {
                    "status": response.status,
                    "headers": dict(response.headers.items()),
                    "body": parsed,
                }
        except error.HTTPError as exc:
            raise ConnectorError(
                "HTTP_ERROR",
                f"HTTP request failed with {exc.code}",
                details={"status": exc.code, "url": url},
            ) from exc
        except error.URLError as exc:
            raise ConnectorError(
                "NETWORK_ERROR",
                f"Network request failed: {exc.reason}",
                details={"url": url},
            ) from exc
