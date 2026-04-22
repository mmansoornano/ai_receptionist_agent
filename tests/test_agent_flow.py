"""Smoke integration tests for the full receptionist graph."""
from __future__ import annotations

import os
from typing import Any

import pytest
from langchain_core.messages import HumanMessage

from tests.llm_test_utils import last_assistant_text, llm_unreachable, make_receptionist_state

pytestmark = pytest.mark.integration


def _llm_configured() -> bool:
    provider = (os.getenv("LLM_PROVIDER") or "ollama").lower().strip()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return True


@pytest.fixture(scope="module")
def receptionist_graph():
    from graph.main import receptionist_graph as graph

    return graph


@pytest.fixture
def base_state():
    def _make(
        content: str,
        *,
        conversation_id: str = "test_conv",
        customer_id: str = "test_customer",
    ):
        return make_receptionist_state(
            content, conversation_id=conversation_id, customer_id=customer_id
        )

    return _make


@pytest.mark.parametrize(
    "user_message",
    [
        "What is the price of protein bars?",
        "Add 2 white chocolate protein bars to my cart",
        "Show me my cart",
    ],
)
def test_receptionist_graph_invoke_returns_assistant_message(
    receptionist_graph, base_state, user_message: str
):
    if not _llm_configured():
        pytest.skip("OPENAI_API_KEY not set for LLM_PROVIDER=openai")

    conv_id = f"test_conv_{abs(hash(user_message)) % 10_000}"
    state = base_state(user_message, conversation_id=conv_id)
    config: dict[str, Any] = {"configurable": {"thread_id": conv_id}}
    try:
        result = receptionist_graph.invoke(state, config)
    except BaseException as exc:
        if llm_unreachable(exc):
            pytest.skip(f"LLM endpoint unreachable: {exc}")
        raise

    assert "messages" in result
    assert result["messages"], "expected non-empty messages"
    text = last_assistant_text(result["messages"])
    assert len(text) >= 8, "expected last assistant message with visible text"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-s", "-m", "integration"]))
