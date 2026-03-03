"""State/memory abstractions for runtime execution."""

from __future__ import annotations

from typing import Any, Protocol


class StateStore(Protocol):
    """Contract for persisting orchestration state."""

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve state by key."""

    def set(self, key: str, value: Any) -> None:
        """Persist state by key."""


class InMemoryStateStore:
    """Simple in-memory implementation of StateStore."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._state[key] = value
