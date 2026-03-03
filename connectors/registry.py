"""Connector registry with versioning and capability discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from connectors.base import BaseConnector


@dataclass(frozen=True)
class ConnectorRecord:
    connector: BaseConnector
    version: str


class ConnectorRegistry:
    """In-memory registry for connector implementations."""

    def __init__(self) -> None:
        self._records: Dict[tuple[str, str], ConnectorRecord] = {}
        self._latest_version: Dict[str, str] = {}

    def register(self, connector: BaseConnector, version: str = "v1") -> None:
        key = (connector.name, version)
        if key in self._records:
            raise ValueError(f"connector already registered: {connector.name}@{version}")

        self._records[key] = ConnectorRecord(connector=connector, version=version)
        self._latest_version[connector.name] = version

    def get(self, name: str, version: str | None = None) -> BaseConnector:
        selected_version = version or self._latest_version.get(name)
        if not selected_version:
            raise KeyError(f"unknown connector: {name}")

        key = (name, selected_version)
        record = self._records.get(key)
        if not record:
            raise KeyError(f"unknown connector version: {name}@{selected_version}")
        return record.connector

    def discover_by_capability(self, capability: str) -> list[str]:
        matching: list[str] = []
        for (name, version), record in self._records.items():
            if capability in record.connector.capabilities:
                matching.append(f"{name}@{version}")
        return sorted(matching)

    def list_connectors(self) -> Iterable[str]:
        for name, version in sorted(self._latest_version.items()):
            yield f"{name}@{version}"
