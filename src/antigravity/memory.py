"""Memory backends for Antigravity (v0.2).

Provides a unified MemoryBackend interface with two production implementations:
  - InMemoryBackend  : fast, volatile, useful for tests and local dev.
  - RedisBackend     : persistent, suitable for single-node or cluster Redis.
  - PostgresBackend  : durable, relational store via psycopg2.

All backends are key-scoped: each workflow run gets its own namespace so
contexts don't bleed across concurrent executions.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------

class MemoryBackend(ABC):
    """Abstract base class for all memory backends."""

    @abstractmethod
    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value under namespace:key with optional TTL in seconds."""

    @abstractmethod
    def get(self, namespace: str, key: str) -> Any | None:
        """Retrieve a value. Returns None if missing or expired."""

    @abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        """Delete a key. Returns True if deleted, False if not found."""

    @abstractmethod
    def keys(self, namespace: str) -> list[str]:
        """List all keys in a namespace."""

    @abstractmethod
    def flush_namespace(self, namespace: str) -> int:
        """Delete all keys in a namespace. Returns count of deleted keys."""

    # Convenience helpers shared by all backends
    def get_or_default(self, namespace: str, key: str, default: Any = None) -> Any:
        val = self.get(namespace, key)
        return val if val is not None else default

    def update(self, namespace: str, key: str, updates: dict[str, Any]) -> None:
        """Shallow-merge updates into an existing dict value."""
        current = self.get(namespace, key) or {}
        if not isinstance(current, dict):
            raise TypeError(f"Cannot update non-dict value at {namespace}:{key}")
        current.update(updates)
        self.set(namespace, key, current)


# ---------------------------------------------------------------------------
# InMemory backend (dev / test)
# ---------------------------------------------------------------------------

@dataclass
class _Entry:
    value: Any
    expires_at: float | None = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() > self.expires_at


class InMemoryBackend(MemoryBackend):
    """Volatile in-process store. Suitable for tests and local development."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, _Entry]] = {}

    def _ns(self, namespace: str) -> dict[str, _Entry]:
        return self._store.setdefault(namespace, {})

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.monotonic() + ttl if ttl is not None else None
        self._ns(namespace)[key] = _Entry(value=value, expires_at=expires_at)

    def get(self, namespace: str, key: str) -> Any | None:
        entry = self._ns(namespace).get(key)
        if entry is None or entry.is_expired():
            return None
        return entry.value

    def delete(self, namespace: str, key: str) -> bool:
        return self._ns(namespace).pop(key, None) is not None

    def keys(self, namespace: str) -> list[str]:
        return [
            k for k, e in self._ns(namespace).items() if not e.is_expired()
        ]

    def flush_namespace(self, namespace: str) -> int:
        ns = self._store.pop(namespace, {})
        return len(ns)


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------

class RedisBackend(MemoryBackend):
    """Redis-backed store using the official redis-py client.

    Install dependency: pip install redis

    Args:
        host: Redis host (default: localhost).
        port: Redis port (default: 6379).
        db:   Redis database index (default: 0).
        client: Pre-built redis.Redis instance (optional, overrides host/port/db).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        client: Any = None,
    ) -> None:
        if client is not None:
            self._r = client
        else:
            try:
                import redis  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "RedisBackend requires the 'redis' package: pip install redis"
                ) from exc
            self._r = redis.Redis(host=host, port=port, db=db, decode_responses=False)

    def _full_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        raw = json.dumps(value).encode()
        if ttl is not None:
            self._r.setex(self._full_key(namespace, key), ttl, raw)
        else:
            self._r.set(self._full_key(namespace, key), raw)

    def get(self, namespace: str, key: str) -> Any | None:
        raw = self._r.get(self._full_key(namespace, key))
        if raw is None:
            return None
        return json.loads(raw)

    def delete(self, namespace: str, key: str) -> bool:
        return bool(self._r.delete(self._full_key(namespace, key)))

    def keys(self, namespace: str) -> list[str]:
        pattern = f"{namespace}:*"
        prefix_len = len(namespace) + 1
        return [
            k.decode()[prefix_len:] if isinstance(k, bytes) else k[prefix_len:]
            for k in self._r.keys(pattern)
        ]

    def flush_namespace(self, namespace: str) -> int:
        pattern = f"{namespace}:*"
        keys = self._r.keys(pattern)
        if keys:
            return self._r.delete(*keys)
        return 0


# ---------------------------------------------------------------------------
# Postgres backend
# ---------------------------------------------------------------------------

class PostgresBackend(MemoryBackend):
    """Postgres-backed store using psycopg2.

    Install dependency: pip install psycopg2-binary

    The backend creates a table ``antigravity_memory`` on first connect.
    Schema::

        CREATE TABLE IF NOT EXISTS antigravity_memory (
            namespace TEXT NOT NULL,
            key       TEXT NOT NULL,
            value     JSONB NOT NULL,
            expires_at DOUBLE PRECISION,
            PRIMARY KEY (namespace, key)
        );
    """

    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS antigravity_memory (
            namespace  TEXT NOT NULL,
            key        TEXT NOT NULL,
            value      JSONB NOT NULL,
            expires_at DOUBLE PRECISION,
            PRIMARY KEY (namespace, key)
        );
    """

    def __init__(self, dsn: str | None = None, conn: Any = None) -> None:
        if conn is not None:
            self._conn = conn
        else:
            try:
                import psycopg2  # type: ignore
            except ImportError as exc:
                raise ImportError(
                    "PostgresBackend requires psycopg2: pip install psycopg2-binary"
                ) from exc
            self._conn = psycopg2.connect(dsn)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(self._CREATE_TABLE)
        self._conn.commit()

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        expires_at = time.time() + ttl if ttl is not None else None
        sql = """
            INSERT INTO antigravity_memory (namespace, key, value, expires_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (namespace, key) DO UPDATE
                SET value = EXCLUDED.value,
                    expires_at = EXCLUDED.expires_at;
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (namespace, key, json.dumps(value), expires_at))
        self._conn.commit()

    def get(self, namespace: str, key: str) -> Any | None:
        sql = "SELECT value, expires_at FROM antigravity_memory WHERE namespace=%s AND key=%s;"
        with self._conn.cursor() as cur:
            cur.execute(sql, (namespace, key))
            row = cur.fetchone()
        if row is None:
            return None
        value_raw, expires_at = row
        if expires_at is not None and time.time() > expires_at:
            return None
        return json.loads(value_raw) if isinstance(value_raw, str) else value_raw

    def delete(self, namespace: str, key: str) -> bool:
        sql = "DELETE FROM antigravity_memory WHERE namespace=%s AND key=%s;"
        with self._conn.cursor() as cur:
            cur.execute(sql, (namespace, key))
            deleted = cur.rowcount
        self._conn.commit()
        return deleted > 0

    def keys(self, namespace: str) -> list[str]:
        sql = """
            SELECT key FROM antigravity_memory
            WHERE namespace=%s AND (expires_at IS NULL OR expires_at > %s);
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, (namespace, time.time()))
            return [row[0] for row in cur.fetchall()]

    def flush_namespace(self, namespace: str) -> int:
        sql = "DELETE FROM antigravity_memory WHERE namespace=%s;"
        with self._conn.cursor() as cur:
            cur.execute(sql, (namespace,))
            deleted = cur.rowcount
        self._conn.commit()
        return deleted


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_memory_backend(backend_type: str = "memory", **kwargs: Any) -> MemoryBackend:
    """Create a memory backend by name.

    Args:
        backend_type: One of 'memory', 'redis', 'postgres', 'semantic'.
        **kwargs: Passed to the backend constructor.

    Returns:
        A MemoryBackend instance.
    """
    if backend_type == "semantic":
        from .memory_semantic import SemanticMemory

        return SemanticMemory(**kwargs)

    backends: dict[str, type[MemoryBackend]] = {
        "memory": InMemoryBackend,
        "redis": RedisBackend,
        "postgres": PostgresBackend,
    }
    if backend_type not in backends:
        supported = [*backends.keys(), "semantic"]
        raise ValueError(f"Unknown backend '{backend_type}'. Choose from: {supported}")
    return backends[backend_type](**kwargs)
