"""Semantic memory backend with dependency-aware fallback behavior."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

from .memory import MemoryBackend


@dataclass
class _SemanticRecord:
    key: str
    value: Any
    text: str
    embedding: list[float] | None


class SemanticMemory(MemoryBackend):
    """Memory backend that supports vector-like semantic search.

    In environments where optional semantic dependencies are unavailable, this
    backend transparently falls back to exact-key matching for compatibility.

    Stub mode can be enabled with ``ANTIGRAVITY_SEMANTIC_STUB=1`` to avoid
    external model/index binaries in CI.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, _SemanticRecord]] = {}
        self._embedder = self._build_embedder()

    def _ns(self, namespace: str) -> dict[str, _SemanticRecord]:
        return self._store.setdefault(namespace, {})

    def _build_embedder(self):
        if os.getenv("ANTIGRAVITY_SEMANTIC_STUB", "").lower() in {"1", "true", "yes"}:
            return self._stub_embed

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError:
            return None

        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            return self._stub_embed

        def _embed(text: str) -> list[float]:
            vec = model.encode(text)
            if hasattr(vec, "tolist"):
                return [float(x) for x in vec.tolist()]
            return [float(x) for x in vec]

        return _embed

    @staticmethod
    def _to_text(value: Any) -> str:
        if isinstance(value, str):
            return value
        return repr(value)

    @staticmethod
    def _stub_embed(text: str) -> list[float]:
        tokens = [tok for tok in text.lower().split() if tok]
        if not tokens:
            return [0.0]
        total = float(len(tokens))
        avg_len = float(sum(len(t) for t in tokens)) / total
        return [total, avg_len]

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        size = min(len(left), len(right))
        if size == 0:
            return 0.0
        dot = sum(left[i] * right[i] for i in range(size))
        ln = math.sqrt(sum(v * v for v in left[:size]))
        rn = math.sqrt(sum(v * v for v in right[:size]))
        if ln == 0.0 or rn == 0.0:
            return 0.0
        return dot / (ln * rn)

    # MemoryBackend contract -------------------------------------------------

    def set(self, namespace: str, key: str, value: Any, ttl: int | None = None) -> None:
        _ = ttl  # TTL is currently not implemented for semantic memory.
        self.store(namespace=namespace, key=key, value=value, embed=True)

    def get(self, namespace: str, key: str) -> Any | None:
        record = self._ns(namespace).get(key)
        if record is None:
            return None
        return record.value

    def delete(self, namespace: str, key: str) -> bool:
        return self._ns(namespace).pop(key, None) is not None

    def keys(self, namespace: str) -> list[str]:
        return list(self._ns(namespace).keys())

    def flush_namespace(self, namespace: str) -> int:
        ns = self._store.pop(namespace, {})
        return len(ns)

    # Semantic API -----------------------------------------------------------

    def store(self, namespace: str, key: str, value: Any, embed: bool = True) -> None:
        text = self._to_text(value)
        embedding = None
        if embed and self._embedder is not None:
            embedding = self._embedder(text)
        self._ns(namespace)[key] = _SemanticRecord(
            key=key,
            value=value,
            text=text,
            embedding=embedding,
        )

    def search(self, namespace: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        records = list(self._ns(namespace).values())
        if not records:
            return []

        # Exact-key compatibility path when semantic dependencies are missing.
        if self._embedder is None:
            match = self._ns(namespace).get(query)
            if match is None:
                return []
            return [{"key": match.key, "value": match.value, "score": 1.0}]

        query_embedding = self._embedder(query)
        scored: list[tuple[float, _SemanticRecord]] = []
        for rec in records:
            embedding = rec.embedding
            if embedding is None:
                continue
            score = self._cosine_similarity(query_embedding, embedding)
            scored.append((score, rec))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {"key": rec.key, "value": rec.value, "score": score}
            for score, rec in scored[:top_k]
        ]
