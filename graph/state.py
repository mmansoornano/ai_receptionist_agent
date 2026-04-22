"""LangGraph state definition for the receptionist agent system."""
from typing import Annotated, Optional, Dict, Sequence, TypedDict
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langgraph.graph.message import add_messages
def sliding_window_messages(existing: list[BaseMessage], new: list[BaseMessage]) -> list[BaseMessage]:
    """
    Maintains a sliding window of the last N messages while preserving tool call/result pairs.
    
    This reducer:
    - APPENDS new messages to existing ones (like add_messages)
    - Maintains a sliding window of MAX_MESSAGES (keeps last N, trims oldest)
    - Preserves tool call/result pairs (AIMessage with tool_calls + ToolMessage stay together)
    - Ensures we always have room for complete conversation turns
    
    Args:
        existing: Current messages in state
        new: New messages to append
    
    Returns:
        Sliding window of messages (up to MAX_MESSAGES, preserving tool pairs)
    """
    MAX_MESSAGES = 50  # Increased to ensure we can show 10+ messages in history
    all_messages = existing + new
    
    if len(all_messages) <= MAX_MESSAGES:
        return all_messages
    
    # Group tool calls with their results to keep them together
    message_groups = []
    i = 0
    while i < len(all_messages):
        msg = all_messages[i]
        
        # If it's an AI message with tool calls, group with following ToolMessages
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            group = [msg]
            # Look for corresponding ToolMessages (may be multiple)
            i += 1
            while i < len(all_messages) and isinstance(all_messages[i], ToolMessage):
                # Match tool message to tool call by tool_call_id
                tool_msg = all_messages[i]
                if hasattr(tool_msg, 'tool_call_id'):
                    tool_call_id = tool_msg.tool_call_id
                    # Check if this tool message matches any tool call in the AI message
                    tool_call_ids = []
                    for tc in msg.tool_calls:
                        if isinstance(tc, dict):
                            tool_call_ids.append(tc.get('id', ''))
                        elif hasattr(tc, 'id'):
                            tool_call_ids.append(tc.id)
                    
                    if tool_call_id in tool_call_ids:
                        group.append(tool_msg)
                        i += 1
                    else:
                        break
                else:
                    group.append(tool_msg)
                    i += 1
            
            message_groups.append(('tool_pair', group))
            continue  # Don't increment i again since we already did
        else:
            message_groups.append(('single', [msg]))
        i += 1
    
    # Now trim from the beginning, keeping groups together
    # We iterate in reverse (most recent first) and prepend groups
    final_messages = []
    for group_type, messages in reversed(message_groups):
        if len(final_messages) + len(messages) <= MAX_MESSAGES:
            final_messages = messages + final_messages
        else:
            # Can't fit the whole group, stop here (preserve most recent messages)
            break
    
    return final_messages

class ReceptionistState(TypedDict):
    """State for the receptionist multi-agent system.
    
    The messages field uses sliding_window_messages reducer which:
    - APPENDS new messages to existing ones (does not replace)
    - Maintains a sliding window of last N messages (MAX_MESSAGES = 50)
    - Preserves tool call/result pairs (AIMessage with tool_calls + ToolMessages stay together)
    - Trims oldest messages when window exceeds MAX_MESSAGES
    - Ensures conversation history can show up to 10+ messages for context
    """
    messages: Annotated[list[BaseMessage], sliding_window_messages]
    intent: Optional[str]  # e.g. product_inquiry, ordering, payment, cancellation, general_qa, greeting, guardrail_refuse
    conversation_context: Optional[str]  # Summary or key context from conversation history for efficient memory
    active_agent: Optional[str]  # Track current active agent node name for stateful routing
    customer_info: Optional[Dict]
    cart_data: Optional[Dict]  # Shopping cart data
    order_data: Optional[Dict]  # Order data
    payment_data: Optional[Dict]  # Payment data
    channel: str  # "voice" or "sms"
    language: str  # "en" (English)
    conversation_id: Optional[str]
    customer_id: Optional[str]
