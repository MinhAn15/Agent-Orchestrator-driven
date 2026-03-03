"""Context handoff primitives for transitioning work between agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, MutableMapping


@dataclass(slots=True)
class HandoffRecord:
    """Represents a single transition between agents."""

    from_agent: str
    to_agent: str
    reason: str
    task_state: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HandoffManager:
    """Transfers selected context fields while keeping a full transition history."""

    def __init__(self, *, default_state_keys: tuple[str, ...] = ("task_id", "goal", "artifacts")) -> None:
        self._default_state_keys = default_state_keys
        self._history: List[HandoffRecord] = []

    def handoff(
        self,
        *,
        from_agent: str,
        to_agent: str,
        task_state: Mapping[str, Any],
        reason: str,
        include_keys: tuple[str, ...] | None = None,
    ) -> Dict[str, Any]:
        """Create handoff payload and append transition history metadata."""

        keys = include_keys or self._default_state_keys
        next_state: MutableMapping[str, Any] = {key: task_state[key] for key in keys if key in task_state}

        history_payload = [self._asdict(item) for item in self._history]
        next_state["handoff"] = {
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
        }
        next_state["handoff_history"] = history_payload

        record = HandoffRecord(
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            task_state=dict(next_state),
        )
        self._history.append(record)
        return dict(next_state)

    def history(self) -> List[Dict[str, Any]]:
        """Read handoff history in chronological order."""

        return [self._asdict(item) for item in self._history]

    @staticmethod
    def _asdict(record: HandoffRecord) -> Dict[str, Any]:
        return {
            "from_agent": record.from_agent,
            "to_agent": record.to_agent,
            "reason": record.reason,
            "task_state": record.task_state,
            "timestamp": record.timestamp,
        }
