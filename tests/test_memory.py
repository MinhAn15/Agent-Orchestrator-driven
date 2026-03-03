"""Tests for MemoryBackend implementations (v0.2) — InMemoryBackend only.
Redis/Postgres are tested via the shared contract suite with a fake client.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from unittest.mock import MagicMock, patch
from antigravity.memory import (
    InMemoryBackend,
    RedisBackend,
    create_memory_backend,
)


# ---------------------------------------------------------------------------
# Contract test mixin — runs the same behaviour tests on every backend
# ---------------------------------------------------------------------------

class MemoryContractTests:
    """Subclass and set self.backend in setup_method."""

    def test_set_and_get(self):
        self.backend.set("ns", "k", "hello")
        assert self.backend.get("ns", "k") == "hello"

    def test_get_missing_returns_none(self):
        assert self.backend.get("ns", "missing") is None

    def test_overwrite_value(self):
        self.backend.set("ns", "k", 1)
        self.backend.set("ns", "k", 2)
        assert self.backend.get("ns", "k") == 2

    def test_delete_existing_key(self):
        self.backend.set("ns", "k", "v")
        assert self.backend.delete("ns", "k") is True
        assert self.backend.get("ns", "k") is None

    def test_delete_missing_key_returns_false(self):
        assert self.backend.delete("ns", "nonexistent") is False

    def test_keys_lists_all(self):
        self.backend.set("ns", "a", 1)
        self.backend.set("ns", "b", 2)
        assert sorted(self.backend.keys("ns")) == ["a", "b"]

    def test_keys_different_namespace_isolated(self):
        self.backend.set("ns1", "x", 1)
        self.backend.set("ns2", "y", 2)
        assert self.backend.keys("ns1") == ["x"]

    def test_flush_namespace(self):
        self.backend.set("ns", "a", 1)
        self.backend.set("ns", "b", 2)
        count = self.backend.flush_namespace("ns")
        assert count == 2
        assert self.backend.keys("ns") == []

    def test_get_or_default(self):
        assert self.backend.get_or_default("ns", "missing", default="fallback") == "fallback"
        self.backend.set("ns", "k", "real")
        assert self.backend.get_or_default("ns", "k", default="fallback") == "real"

    def test_update_merges_dict(self):
        self.backend.set("ns", "ctx", {"a": 1, "b": 2})
        self.backend.update("ns", "ctx", {"b": 99, "c": 3})
        assert self.backend.get("ns", "ctx") == {"a": 1, "b": 99, "c": 3}

    def test_update_raises_on_non_dict(self):
        self.backend.set("ns", "k", "not-a-dict")
        with pytest.raises(TypeError):
            self.backend.update("ns", "k", {"x": 1})

    def test_complex_value_roundtrip(self):
        val = {"list": [1, 2, 3], "nested": {"deep": True}}
        self.backend.set("ns", "complex", val)
        assert self.backend.get("ns", "complex") == val


# ---------------------------------------------------------------------------
# InMemoryBackend concrete tests
# ---------------------------------------------------------------------------

class TestInMemoryBackend(MemoryContractTests):
    def setup_method(self):
        self.backend = InMemoryBackend()

    def test_ttl_expiry(self):
        self.backend.set("ns", "shortlived", "value", ttl=1)
        assert self.backend.get("ns", "shortlived") == "value"
        time.sleep(1.1)
        assert self.backend.get("ns", "shortlived") is None

    def test_ttl_key_excluded_from_keys_after_expiry(self):
        self.backend.set("ns", "expires", "v", ttl=1)
        self.backend.set("ns", "permanent", "v")
        time.sleep(1.1)
        assert "expires" not in self.backend.keys("ns")
        assert "permanent" in self.backend.keys("ns")


# ---------------------------------------------------------------------------
# RedisBackend contract tests with a fake client
# ---------------------------------------------------------------------------

class FakeRedis:
    """Minimal Redis fake that wraps InMemoryBackend for contract testing."""

    def __init__(self):
        self._store: dict[bytes, bytes] = {}

    def set(self, key, value):
        self._store[key] = value

    def setex(self, key, ttl, value):
        self._store[key] = value  # TTL not simulated in fake

    def get(self, key):
        return self._store.get(key)

    def delete(self, *keys):
        deleted = sum(1 for k in keys if self._store.pop(k, None) is not None)
        return deleted

    def keys(self, pattern):
        prefix = pattern.rstrip("*")
        return [k for k in self._store if k.startswith(prefix)]


class TestRedisBackend(MemoryContractTests):
    def setup_method(self):
        self.backend = RedisBackend(client=FakeRedis())


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestCreateMemoryBackend:
    def test_memory_backend(self):
        b = create_memory_backend("memory")
        assert isinstance(b, InMemoryBackend)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            create_memory_backend("unknown")
