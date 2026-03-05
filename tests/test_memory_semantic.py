"""Tests for semantic memory backend."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antigravity.memory import create_memory_backend
from antigravity.memory_semantic import SemanticMemory


def test_semantic_search_happy_path_stub_mode(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_SEMANTIC_STUB", "1")
    backend = SemanticMemory()

    backend.store("ns", "msg1", "apple banana")
    backend.store("ns", "msg2", "banana orange grape")

    results = backend.search("ns", "banana", top_k=2)

    assert len(results) == 2
    assert results[0]["score"] >= results[1]["score"]
    assert {r["key"] for r in results} == {"msg1", "msg2"}


def test_semantic_missing_dependency_exact_key_fallback(monkeypatch):
    monkeypatch.delenv("ANTIGRAVITY_SEMANTIC_STUB", raising=False)
    monkeypatch.setattr(SemanticMemory, "_build_embedder", lambda self: None)

    backend = SemanticMemory()
    backend.store("ns", "known-key", {"payload": 1}, embed=True)

    assert backend.search("ns", "known-key") == [
        {"key": "known-key", "value": {"payload": 1}, "score": 1.0}
    ]
    assert backend.search("ns", "not-a-key") == []


def test_factory_routes_semantic_backend(monkeypatch):
    monkeypatch.setenv("ANTIGRAVITY_SEMANTIC_STUB", "1")
    backend = create_memory_backend("semantic")
    assert isinstance(backend, SemanticMemory)
