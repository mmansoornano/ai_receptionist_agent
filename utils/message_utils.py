"""Utility functions for handling message state updates."""
from typing import List
from langchain_core.messages import BaseMessage
from langgraph.types import Command
from utils.logger import log_agent_flow


def create_message_update_command(
    new_messages: List[BaseMessage],
    state: dict = None,
    goto: str = None,
    **other_updates
) -> Command:
    """Create a Command with message update that will APPEND new messages to existing ones.
    
    The add_messages reducer in state will automatically APPEND new_messages
    to existing messages in state. Old messages are PRESERVED.
    
    CRITICAL: We only return NEW messages - the add_messages reducer handles appending.
    State will contain: [old_messages..., new_messages...]
    
    Args:
        new_messages: List of NEW messages to append (can be single message in list)
        state: Optional current state to log existing message count
        goto: Optional next node name for routing
        **other_updates: Any other state updates (intent, active_agent, etc.)
    
    Returns:
        Command object with update dict that includes ONLY new messages
        The reducer will append these to existing messages in state
    """
    # Validate that we have messages
    if not isinstance(new_messages, list):
        new_messages = [new_messages] if new_messages else []
    
    # IMPORTANT: We return ONLY new messages here
    # The add_messages reducer will automatically:
    # 1. Take existing messages from state
    # 2. Append new_messages to them
    # 3. Preserve ALL old messages
    # Result: [all_existing_messages..., new_messages...]
    update_dict = {"messages": new_messages}
    update_dict.update(other_updates)
    
    # Log message appending for debugging
    existing_count = len(state.get("messages", [])) if state else 0
    log_agent_flow("MESSAGE_UPDATE", "Appending NEW messages to existing state", {
        "existing_message_count": existing_count,
        "new_message_count": len(new_messages),
        "message_types": [type(msg).__name__ for msg in new_messages],
        "has_other_updates": len(other_updates) > 0,
        "total_after_append": existing_count + len(new_messages),
        "goto": goto,
        "reducer": "add_messages (appends, preserves old)"
    })
    
    # Command constructor takes update and goto as separate parameters
    # The update contains ONLY new messages - reducer appends to existing
    return Command(update=update_dict, goto=goto) if goto else Command(update=update_dict)


def ensure_messages_preserved(
    current_messages: List[BaseMessage],
    new_messages: List[BaseMessage]
) -> List[BaseMessage]:
    """Ensure old messages are preserved when adding new ones.
    
    This is a safety function - the add_messages reducer should handle this,
    but this can be used for explicit validation.
    
    Args:
        current_messages: Existing messages in state
        new_messages: New messages to add
    
    Returns:
        Combined list with old messages first, then new messages
    """
    if not isinstance(new_messages, list):
        new_messages = [new_messages] if new_messages else []
    
    # Explicitly preserve old messages
    preserved_messages = list(current_messages) if current_messages else []
    preserved_messages.extend(new_messages)
    
    return preserved_messages