"""Handoff primitives backed by ``MemoryBackend``."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from antigravity.memory import InMemoryBackend, MemoryBackend


@dataclass(frozen=True)
class HandoffToken:
    """Transfer payload used when work is escalated between agents."""

    from_agent: str
    to_agent: str
    task_id: str
    context_snapshot: dict[str, Any]
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HandoffBus:
    """FIFO handoff queue persisted to memory backend namespaces."""

    def __init__(
        self,
        memory_backend: MemoryBackend | None = None,
        *,
        namespace: str = "handoff",
    ) -> None:
        self.memory_backend = memory_backend or InMemoryBackend()
        self.namespace = namespace

    def transfer(self, token: HandoffToken) -> HandoffToken:
        """Append a handoff token to the recipient queue."""
        queue_key = self._queue_key(token.to_agent)
        queue = self.memory_backend.get_or_default(self.namespace, queue_key, default=[])
        queue.append(asdict(token))
        self.memory_backend.set(self.namespace, queue_key, queue)
        return token

    def receive(self, to_agent: str) -> HandoffToken | None:
        """Pop the oldest available token for ``to_agent``."""
        queue_key = self._queue_key(to_agent)
        queue = self.memory_backend.get_or_default(self.namespace, queue_key, default=[])
        if not queue:
            return None
        item = queue.pop(0)
        self.memory_backend.set(self.namespace, queue_key, queue)
        return HandoffToken(**item)

    @staticmethod
    def _queue_key(to_agent: str) -> str:
        return f"queue:{to_agent}"
