"""Tests for LLM Policy Engine (v0.4)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from llm_policy import (
    Message,
    PolicyResult,
    StubProvider,
    LLMPolicyEngine,
    create_engine,
    PROVIDER_REGISTRY,
)


class TestMessage:
    def test_message_fields(self):
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"


class TestStubProvider:
    def test_default_response(self):
        p = StubProvider()
        result = p.complete([Message(role="user", content="test")])
        assert result.content == "[stub response]"
        assert result.provider == "stub"
        assert result.model == "stub-1.0"

    def test_custom_response(self):
        p = StubProvider(response="custom")
        result = p.complete([])
        assert result.content == "custom"

    def test_usage_zeros(self):
        p = StubProvider()
        result = p.complete([])
        assert result.usage["total_tokens"] == 0

    def test_name(self):
        assert StubProvider().name == "stub"


class TestLLMPolicyEngine:
    def test_decide_returns_result(self):
        engine = LLMPolicyEngine()
        result = engine.decide(task="summarise this")
        assert isinstance(result, PolicyResult)
        assert result.content == "[stub response]"

    def test_decide_with_context(self):
        engine = LLMPolicyEngine()
        result = engine.decide(task="do something", context="You are a helper.")
        assert result.content is not None

    def test_chat_interface(self):
        engine = LLMPolicyEngine()
        msgs = [Message(role="user", content="ping")]
        result = engine.chat(msgs)
        assert isinstance(result, PolicyResult)

    def test_swap_provider(self):
        engine = LLMPolicyEngine()
        new_provider = StubProvider(response="swapped")
        engine.swap_provider(new_provider)
        assert engine.provider.name == "stub"
        result = engine.decide(task="test")
        assert result.content == "swapped"

    def test_provider_property(self):
        p = StubProvider()
        engine = LLMPolicyEngine(provider=p)
        assert engine.provider is p

    def test_custom_system_prompt(self):
        engine = LLMPolicyEngine(system_prompt="Custom system.")
        result = engine.decide(task="anything")
        assert isinstance(result, PolicyResult)


class TestCreateEngine:
    def test_create_stub(self):
        engine = create_engine("stub")
        assert isinstance(engine, LLMPolicyEngine)
        assert engine.provider.name == "stub"

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_engine("nonexistent")

    def test_provider_registry_has_defaults(self):
        assert "stub" in PROVIDER_REGISTRY
        assert "openai" in PROVIDER_REGISTRY
        assert "ollama" in PROVIDER_REGISTRY
