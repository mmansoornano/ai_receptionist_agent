"""Utility functions for formatting conversation history."""
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from utils.logger import log_conversation_history


def format_conversation_history(messages, max_messages=10, include_system=False):
    """Format conversation history for agent context.
    
    Args:
        messages: List of messages from state (should be TRIMMED messages matching what LLM sees)
        max_messages: Maximum number of recent messages to include (default: 10)
        include_system: Whether to include SystemMessage (default: False)
    
    Returns:
        Formatted conversation history string, or None if no history
    """
    if not messages:
        log_conversation_history("No messages to format conversation history")
        return None
    
    # Debug: log input message types
    input_types = [type(msg).__name__ for msg in messages[:5]]  # First 5 for debugging
    log_conversation_history(f"Input messages: {len(messages)} total, types (first 5): {input_types}")
    
    # Filter messages - ONLY show dispatched messages (user and assistant messages that were actually sent)
    # EXCLUDE: ToolMessages, SystemMessages (unless include_system=True), and AIMessages with only tool calls (no content)
    filtered_messages = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            if include_system:
                filtered_messages.append(msg)
            # Skip SystemMessages by default
            continue
        elif isinstance(msg, ToolMessage):
            # Skip ToolMessages - these are internal tool execution results, not dispatched messages
            continue
        elif isinstance(msg, HumanMessage):
            # Include all HumanMessages (user messages)
            filtered_messages.append(msg)
        elif isinstance(msg, AIMessage):
            # Include AIMessages that have content OR tool calls
            # Messages with tool calls are part of the conversation flow, even if no text content
            # We need to see them in history to understand the conversation progression
            if msg.content and msg.content.strip():
                filtered_messages.append(msg)
            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                # Include AIMessages with tool calls even if no content - they're part of conversation
                # Show a summary instead of full tool call details by creating new AIMessage with summary content
                tool_names = []
                for tc in msg.tool_calls:
                    if isinstance(tc, dict):
                        tool_names.append(tc.get('name', 'unknown'))
                    elif hasattr(tc, 'name'):
                        tool_names.append(tc.name)
                tool_summary = f"[Assistant called tool(s): {', '.join(tool_names)}]" if tool_names else "[Assistant made tool calls]"
                # Create a simplified version for history display
                summary_msg = AIMessage(content=tool_summary)
                filtered_messages.append(summary_msg)
    
    if not filtered_messages:
        log_conversation_history("No filtered messages to format conversation history")
        return None
    
    # Get recent messages (last N messages)
    # User wants ALL messages between user and bot, so we take all filtered messages (up to max_messages limit)
    # If there are fewer than max_messages, show all of them
    recent_messages = filtered_messages[-max_messages:] if len(filtered_messages) > max_messages else filtered_messages
    
    # Check if this is the start of conversation (only one user message, no AI responses yet)
    user_message_count = sum(1 for msg in recent_messages if isinstance(msg, HumanMessage))
    ai_message_count = sum(1 for msg in recent_messages if isinstance(msg, AIMessage))
    
    # Debug logging to understand what messages we have
    msg_types = [type(msg).__name__ for msg in recent_messages]
    log_conversation_history(f"Filtered messages: {len(recent_messages)} total, {user_message_count} human, {ai_message_count} ai. Types: {msg_types}")
    
    # If only one user message and no AI responses, it's the start - return None
    # BUT: If we have multiple user messages OR any AI messages, we have history
    if user_message_count <= 1 and ai_message_count == 0:
        log_conversation_history("Only one user message and no AI responses, returning None")
        return None
    
    history_parts = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            if msg.content:
                history_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            # Only show actual content that was dispatched to user (no tool call indicators)
            if msg.content and msg.content.strip():
                history_parts.append(f"Assistant: {msg.content}")
        elif isinstance(msg, SystemMessage) and include_system:
            if msg.content:
                history_parts.append(f"System: {msg.content}")
    
    if not history_parts:
        log_conversation_history("No history parts to format conversation history")
        return None
    
    result = "\n".join(history_parts)
    log_conversation_history(result)
    return result


def get_conversation_summary(messages, max_messages=10):
    """Get a summary of conversation history for context.
    
    Args:
        messages: List of messages from state
        max_messages: Maximum number of recent messages to include
    
    Returns:
        Formatted conversation summary string, or None if no history
    """
    return format_conversation_history(messages, max_messages, include_system=False)
