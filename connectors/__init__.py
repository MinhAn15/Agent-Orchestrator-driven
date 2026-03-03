"""Connector SDK package."""

from connectors.base import BaseConnector, ConnectorContext, ConnectorError
from connectors.filesystem_connector import FilesystemConnector
from connectors.github_connector import GitHubConnector
from connectors.http_connector import HTTPConnector
from connectors.registry import ConnectorRegistry

__all__ = [
    "BaseConnector",
    "ConnectorContext",
    "ConnectorError",
    "ConnectorRegistry",
    "HTTPConnector",
    "FilesystemConnector",
    "GitHubConnector",
]
