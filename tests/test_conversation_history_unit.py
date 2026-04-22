"""Unit tests for format_conversation_history."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from utils.conversation_history import format_conversation_history


def test_empty_messages_returns_none():
    assert format_conversation_history([]) is None
    assert format_conversation_history(None) is None  # type: ignore[arg-type]


def test_single_user_message_no_ai_returns_none():
    messages = [HumanMessage(content="Only user")]
    assert format_conversation_history(messages) is None


def test_user_and_assistant_produces_history():
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi, how can I help?"),
    ]
    out = format_conversation_history(messages)
    assert out is not None
    assert "User: Hello" in out
    assert "Assistant: Hi, how can I help?" in out


def test_tool_messages_filtered_out():
    messages = [
        HumanMessage(content="Q1"),
        AIMessage(content="", tool_calls=[{"name": "get_cart", "id": "1", "args": {}}]),
        ToolMessage(content='{"items":[]}', tool_call_id="1"),
        AIMessage(content="Here is your cart."),
    ]
    out = format_conversation_history(messages)
    assert out is not None
    assert "User: Q1" in out
    assert "Assistant: Here is your cart." in out
    assert "items" not in out or '{"items"' not in out  # tool payload not in formatted user/assistant lines


def test_ai_with_only_tool_calls_gets_summary_line():
    messages = [
        HumanMessage(content="Show cart"),
        AIMessage(content="", tool_calls=[{"name": "view_cart", "id": "x", "args": {}}]),
        AIMessage(content="Done."),
    ]
    out = format_conversation_history(messages)
    assert out is not None
    assert "Assistant called tool" in out
    assert "view_cart" in out


def test_max_messages_trims_older_turns():
    messages = []
    for i in range(12):
        messages.append(HumanMessage(content=f"u{i}"))
        messages.append(AIMessage(content=f"a{i}"))
    out = format_conversation_history(messages, max_messages=4)
    assert out is not None
    assert "u0" not in out
    assert "u11" in out or "a11" in out


def test_include_system_message():
    messages = [
        SystemMessage(content="You are a bot"),
        HumanMessage(content="Hi"),
        AIMessage(content="Hello"),
    ]
    out = format_conversation_history(messages, include_system=True)
    assert out is not None
    assert "System: You are a bot" in out
