---
description: Scaffold a new connector (skill) — create file, register, write test
---

## Prerequisites

- The project is installed (`pip install -e ".[dev]"`)
- You know the connector name (e.g., `jira`, `notion`, `redis`)

## Steps

1. **Create the connector file** at `connectors/<name>_connector.py` using this template:

```python
"""<Name> connector for Antigravity orchestration."""

from __future__ import annotations

from typing import Any

from connectors.base import BaseConnector


class <Name>Connector(BaseConnector):
    """Connect to <Name> service."""

    name = "<name>"

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs

    def execute(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action against <Name>."""
        if action == "health":
            return {"status": "ok", "connector": self.name}
        raise NotImplementedError(f"Action '{action}' not implemented for {self.name}")
```

1. **Register the connector** — add an import in `connectors/__init__.py`:

```python
from .{name}_connector import {Name}Connector
```

1. **Create a test file** at `tests/connectors/test_{name}_connector.py`:

```python
"""Tests for {Name}Connector."""

from connectors.{name}_connector import {Name}Connector


def test_{name}_health_check() -> None:
    connector = {Name}Connector()
    result = connector.execute("health", {})
    assert result["status"] == "ok"
    assert result["connector"] == "{name}"


def test_{name}_unknown_action_raises() -> None:
    connector = {Name}Connector()
    try:
        connector.execute("unknown_action", {})
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass
```

1. **Run tests** to verify:

```bash
pytest tests/connectors/test_{name}_connector.py -v
```

1. **Update `README.md`** — add the new connector to the Skills table in the "Core concepts → Skills" section.

## Success criteria

- `connectors/<name>_connector.py` exists and extends `BaseConnector`
- Connector is importable from `connectors` package
- Test file passes with 2+ tests
- README Skills table includes the new connector
