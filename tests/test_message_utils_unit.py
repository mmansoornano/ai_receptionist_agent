"""Unit tests for message_utils."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from utils.message_utils import create_message_update_command


def test_create_message_update_command_messages_only():
    new_msgs = [AIMessage(content="Reply")]
    cmd = create_message_update_command(new_msgs)
    assert isinstance(cmd, Command)
    assert not cmd.goto
    assert cmd.update["messages"] == new_msgs


def test_create_message_update_command_with_goto_and_updates():
    new_msgs = [HumanMessage(content="X")]
    cmd = create_message_update_command(
        new_msgs,
        state={"messages": [HumanMessage(content="old")]},
        goto="qa_agent",
        intent="general_qa",
        active_agent="qa_agent",
    )
    assert cmd.goto == "qa_agent"
    assert cmd.update["messages"] == new_msgs
    assert cmd.update["intent"] == "general_qa"
    assert cmd.update["active_agent"] == "qa_agent"


def test_create_message_update_command_wraps_single_non_list():
    msg = AIMessage(content="one")
    cmd = create_message_update_command(msg)  # type: ignore[arg-type]
    assert cmd.update["messages"] == [msg]
