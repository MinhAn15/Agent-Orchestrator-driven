"""Connector base contracts for Antigravity orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ConnectorContext:
    """Runtime context passed into each connector invocation."""

    request_id: str
    actor: str = "system"
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ConnectorError(RuntimeError):
    """Normalized connector error type with a machine-readable code."""

    def __init__(self, code: str, message: str, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class BaseConnector(ABC):
    """Shared interface that all connectors must implement."""

    name: str
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def invoke(self, input: Mapping[str, Any], context: ConnectorContext) -> Mapping[str, Any]:
        """Execute connector operation and return a normalized mapping."""
        raise NotImplementedError
