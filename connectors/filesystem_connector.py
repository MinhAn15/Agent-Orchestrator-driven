"""Safe local filesystem connector."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from connectors.base import BaseConnector, ConnectorContext, ConnectorError


class FilesystemConnector(BaseConnector):
    name = "filesystem"
    capabilities = ("fs:read", "fs:list", "fs:write")

    def __init__(self, root_dir: str, read_only: bool = False) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.read_only = read_only

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root_dir / relative_path).resolve()
        if self.root_dir not in (candidate, *candidate.parents):
            raise ConnectorError("ACCESS_DENIED", "Path escapes connector root", {"path": relative_path})
        return candidate

    def invoke(self, input: Mapping[str, Any], context: ConnectorContext) -> Mapping[str, Any]:
        action = input.get("action")
        path = input.get("path", "")

        if action not in {"read", "list", "write"}:
            raise ConnectorError("INVALID_INPUT", "'action' must be one of read/list/write")

        target = self._resolve(path)

        if action == "read":
            if not target.exists() or not target.is_file():
                raise ConnectorError("NOT_FOUND", "File not found", {"path": path})
            return {"path": path, "content": target.read_text(encoding="utf-8")}

        if action == "list":
            if not target.exists() or not target.is_dir():
                raise ConnectorError("NOT_FOUND", "Directory not found", {"path": path})
            return {
                "path": path,
                "entries": sorted(p.name for p in target.iterdir()),
            }

        if self.read_only:
            raise ConnectorError("READ_ONLY", "Connector is in read-only mode")

        content = input.get("content")
        if not isinstance(content, str):
            raise ConnectorError("INVALID_INPUT", "'content' must be a string for write")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8")), "request_id": context.request_id}
