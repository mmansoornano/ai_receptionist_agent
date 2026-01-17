"""Utilities for filtering and processing messages for agents."""
from typing import List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from utils.logger import agent_logger, log_agent_flow


def filter_messages_for_agent(
    messages: List[BaseMessage],
    include_system: bool = False,
    include_tool_results: bool = False
) -> List[BaseMessage]:
    """Filter messages for agent processing.
    
    This filters out messages that shouldn't be processed by the agent:
    - ToolMessages (by default) - internal tool execution results
    - SystemMessages (by default) - system prompts are added separately
    
    Args:
        messages: List of messages to filter
        include_system: Whether to include SystemMessages (default: False)
        include_tool_results: Whether to include ToolMessages (default: False)
    
    Returns:
        Filtered list of messages
    """
    filtered = []
    
    for msg in messages:
        if isinstance(msg, SystemMessage):
            if include_system:
                filtered.append(msg)
            # Skip SystemMessages by default (added separately in prompts)
            continue
        elif isinstance(msg, ToolMessage):
            if include_tool_results:
                filtered.append(msg)
            # Skip ToolMessages by default (internal tool execution results)
            continue
        elif isinstance(msg, (HumanMessage, AIMessage)):
            # Always include HumanMessage and AIMessage (dispatched messages)
            filtered.append(msg)
    
    agent_logger.debug(f"Filtered {len(messages)} messages -> {len(filtered)} messages (include_system={include_system}, include_tool_results={include_tool_results})")
    
    return filtered


def get_last_human_message(messages: List[BaseMessage]) -> BaseMessage | None:
    """Get the last human message from the message list.
    
    Args:
        messages: List of messages
    
    Returns:
        Last HumanMessage or None if not found
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg
    return None


def get_last_ai_message(messages: List[BaseMessage]) -> BaseMessage | None:
    """Get the last AI message from the message list.
    
    Args:
        messages: List of messages
    
    Returns:
        Last AIMessage or None if not found
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def has_tool_calls_in_messages(messages: List[BaseMessage]) -> bool:
    """Check if any message in the list has tool calls.
    
    Args:
        messages: List of messages
    
    Returns:
        True if any message has tool calls, False otherwise
    """
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            return True
    return False


def extract_tool_call_names(messages: List[BaseMessage]) -> List[str]:
    """Extract all tool call names from messages.
    
    Args:
        messages: List of messages
    
    Returns:
        List of tool call names
    """
    tool_names = []
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    tool_names.append(tc.get('name', 'unknown'))
                elif hasattr(tc, 'name'):
                    tool_names.append(tc.name)
    return tool_names
