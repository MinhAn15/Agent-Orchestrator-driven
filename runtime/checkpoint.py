"""Step-level checkpoint persistence for resumable workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(slots=True)
class CheckpointStore:
    """File-based checkpoint store keyed by workflow and step."""

    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_step(self, workflow_id: str, step_id: str, state: Dict[str, Any]) -> Path:
        checkpoint = {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "state": state,
        }
        path = self._path(workflow_id, step_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_step(self, workflow_id: str, step_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(workflow_id, step_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def latest_step(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        workflow_dir = self.base_dir / workflow_id
        if not workflow_dir.exists():
            return None
        candidates = sorted(workflow_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return None
        return json.loads(candidates[0].read_text(encoding="utf-8"))

    def _path(self, workflow_id: str, step_id: str) -> Path:
        safe_step = step_id.replace("/", "_")
        return self.base_dir / workflow_id / f"{safe_step}.json"
