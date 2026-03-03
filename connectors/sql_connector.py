"""SQL connector for Antigravity (v0.3).

Executes parameterised SQL queries against any DBAPI2-compatible database
(SQLite, Postgres, MySQL, etc.). Uses Python's built-in sqlite3 by default
so that tests can run without any external dependencies.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class QueryResult:
    """Wraps the output of a SQL query."""

    rows: list[dict[str, Any]]
    rowcount: int
    description: list[str]

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def scalar(self) -> Any | None:
        row = self.first()
        if row is None:
            return None
        return next(iter(row.values()))

    def __len__(self) -> int:
        return len(self.rows)


@dataclass
class SQLConnector:
    """DBAPI2-compatible SQL connector.

    Args:
        dsn:        SQLite file path or any DSN string (unused for sqlite3).
        driver:     Module name for the DBAPI2 driver (default: 'sqlite3').
        connection: Pre-existing connection object (takes priority over dsn).
        connect_kwargs: Extra kwargs forwarded to the driver's connect().
    """

    dsn: str = ":memory:"
    driver: str = "sqlite3"
    connection: Any = None
    connect_kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.connection is None:
            self.connection = self._connect()

    def _connect(self) -> Any:
        if self.driver == "sqlite3":
            conn = sqlite3.connect(self.dsn, **self.connect_kwargs)
            conn.row_factory = sqlite3.Row
            return conn
        import importlib
        mod = importlib.import_module(self.driver)
        return mod.connect(self.dsn, **self.connect_kwargs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> QueryResult:
        """Execute a single statement and return a QueryResult.

        Args:
            sql:    Parameterised SQL string.
            params: Positional tuple or named dict of bind parameters.

        Returns:
            QueryResult with rows as list[dict].
        """
        cur = self.connection.cursor()
        cur.execute(sql, params)
        self.connection.commit()
        columns = [d[0] for d in (cur.description or [])]
        raw_rows = cur.fetchall() or []
        rows = [dict(zip(columns, row)) for row in raw_rows]
        return QueryResult(rows=rows, rowcount=cur.rowcount, description=columns)

    def execute_many(self, sql: str, params_seq: list[Sequence[Any] | dict[str, Any]]) -> int:
        """Execute a statement for each item in params_seq.

        Returns:
            Total number of affected rows.
        """
        cur = self.connection.cursor()
        cur.executemany(sql, params_seq)
        self.connection.commit()
        return cur.rowcount

    def query(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[dict[str, Any]]:
        """Convenience wrapper — returns rows directly."""
        return self.execute(sql, params).rows

    def close(self) -> None:
        """Close the underlying database connection."""
        self.connection.close()

    def __enter__(self) -> SQLConnector:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
