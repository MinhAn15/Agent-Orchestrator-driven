"""LLM-driven Policy Engine (v0.4).

Routes tasks to the appropriate LLM backend using a pluggable provider
interface. Supports OpenAI-compatible APIs, local Ollama endpoints, and
a stub provider for offline/testing use.
"""
from __future__ import annotations

import abc
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Message:
    """A single conversation message."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class PolicyResult:
    """Result returned by the policy engine."""

    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    def complete(self, messages: List[Message], **kwargs: Any) -> PolicyResult:
        """Send messages and return completion."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier."""


class StubProvider(LLMProvider):
    """Offline stub provider — returns deterministic responses for testing."""

    def __init__(self, response: str = "[stub response]") -> None:
        self._response = response

    @property
    def name(self) -> str:
        return "stub"

    def complete(self, messages: List[Message], **kwargs: Any) -> PolicyResult:
        return PolicyResult(
            content=self._response,
            model="stub-1.0",
            provider=self.name,
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider (works with OpenAI, Azure OpenAI, Together, etc.)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: int = 30,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "openai"

    def complete(self, messages: List[Message], **kwargs: Any) -> PolicyResult:
        try:
            import urllib.request
            import json

            payload = {
                "model": kwargs.get("model", self._model),
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                **{k: v for k, v in kwargs.items() if k != "model"},
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base_url}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read())
            choice = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            return PolicyResult(
                content=choice,
                model=body.get("model", self._model),
                provider=self.name,
                usage=usage,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc


class OllamaProvider(LLMProvider):
    """Local Ollama provider (http://localhost:11434 by default)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    def complete(self, messages: List[Message], **kwargs: Any) -> PolicyResult:
        try:
            import urllib.request
            import json

            payload = {
                "model": kwargs.get("model", self._model),
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self._base_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read())
            content = body["message"]["content"]
            return PolicyResult(
                content=content,
                model=body.get("model", self._model),
                provider=self.name,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Ollama request failed: {exc}") from exc


class LLMPolicyEngine:
    """Routes orchestrator decisions through an LLM provider.

    Usage::

        engine = LLMPolicyEngine(provider=OpenAIProvider())
        result = engine.decide(
            context="You are an orchestrator.",
            task="Summarise the incident report.",
        )
        print(result.content)
    """

    DEFAULT_SYSTEM = (
        "You are an intelligent orchestration agent. "
        "Analyse the task and respond with a clear, concise action plan."
    )

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._provider: LLMProvider = provider or StubProvider()
        self._system = system_prompt or self.DEFAULT_SYSTEM

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decide(self, task: str, context: Optional[str] = None, **kwargs: Any) -> PolicyResult:
        """Ask the LLM to decide on the next action for *task*."""
        system = context or self._system
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=task),
        ]
        return self._provider.complete(messages, **kwargs)

    def chat(self, messages: List[Message], **kwargs: Any) -> PolicyResult:
        """Low-level multi-turn chat interface."""
        return self._provider.complete(messages, **kwargs)

    @property
    def provider(self) -> LLMProvider:
        return self._provider

    def swap_provider(self, provider: LLMProvider) -> None:
        """Hot-swap the underlying LLM provider at runtime."""
        self._provider = provider


# ---------------------------------------------------------------------------
# Registry of built-in providers
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: Dict[str, type] = {
    "stub": StubProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def create_engine(provider_name: str = "stub", **provider_kwargs: Any) -> LLMPolicyEngine:
    """Factory helper: create an :class:`LLMPolicyEngine` by provider name.

    Example::

        engine = create_engine("openai", model="gpt-4o")
    """
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Available: {list(PROVIDER_REGISTRY.keys())}"
        )
    provider_cls = PROVIDER_REGISTRY[provider_name]
    return LLMPolicyEngine(provider=provider_cls(**provider_kwargs))
