"""Utility functions for managing conversation state."""
from typing import Optional
from langchain_core.messages import AIMessage
from graph.main import receptionist_graph
from utils.logger import agent_logger, log_agent_flow


def get_thread_id(conversation_id: Optional[str] = None, customer_id: Optional[str] = None, phone_number: Optional[str] = None) -> str:
    """Generate thread_id for state persistence."""
    return conversation_id or f"conversation-{customer_id}" or f"conversation-{phone_number}" or "conversation-default"


def get_config(thread_id: str) -> dict:
    """Create config dict with thread_id for checkpointer."""
    return {"configurable": {"thread_id": thread_id}}


def reset_conversation_state(
    conversation_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    phone_number: Optional[str] = None
) -> bool:
    """Reset conversation state by clearing checkpointer for the given thread_id.
    
    Args:
        conversation_id: Optional conversation ID
        customer_id: Optional customer ID
        phone_number: Optional phone number
    
    Returns:
        bool: Success status
    """
    try:
        thread_id = get_thread_id(conversation_id, customer_id, phone_number)
        config = get_config(thread_id)
        
        # Clear state by creating empty state update
        empty_state = {
            "messages": [],
            "intent": None,
            "conversation_context": None,
            "active_agent": None,
            "customer_info": None,
            "cart_data": None,
            "order_data": None,
            "payment_data": None,
        }
        
        # Update state to empty values (checkpointer will store this)
        receptionist_graph.update_state(config, empty_state)
        
        agent_logger.info(f"✅ Conversation reset successfully for thread_id: {thread_id}")
        log_agent_flow("SYSTEM", "Conversation Reset", {"thread_id": thread_id})
        
        return True
    except Exception as e:
        agent_logger.error(f"❌ Error resetting conversation state: {e}")
        log_agent_flow("SYSTEM", "Conversation Reset Failed", {"error": str(e)})
        return False


def add_system_message(
    message: str,
    conversation_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    phone_number: Optional[str] = None,
    message_type: str = "system_notification",
    additional_kwargs: Optional[dict] = None
) -> bool:
    """Add a system-generated message to the conversation state without triggering agent processing.
    
    This is useful for:
    - System notifications
    - Reminders
    - Confirmation messages
    - Other non-user-initiated messages
    
    Args:
        message: The content of the system message
        conversation_id: Optional conversation ID
        customer_id: Optional customer ID
        phone_number: Optional phone number
        message_type: Type of system message (for metadata)
        additional_kwargs: Optional additional metadata for the message
    
    Returns:
        bool: Success status
    """
    try:
        thread_id = get_thread_id(conversation_id, customer_id, phone_number)
        config = get_config(thread_id)
        
        # Get current state
        current_state = receptionist_graph.get_state(config)
        current_values = current_state.values if current_state.values else {}
        
        # Create system message with metadata
        msg_kwargs = {"message_type": message_type}
        if additional_kwargs:
            msg_kwargs.update(additional_kwargs)
        
        system_msg = AIMessage(content=message, additional_kwargs=msg_kwargs)
        
        # Update state with system message (reducer will append to existing messages)
        update_state = {
            "messages": [system_msg],
            # Preserve other state values
            "customer_id": current_values.get("customer_id"),
            "conversation_id": current_values.get("conversation_id"),
        }
        
        receptionist_graph.update_state(config, update_state)
        
        agent_logger.info(f"✅ System message added: {message_type} for thread_id: {thread_id}")
        log_agent_flow("SYSTEM", "System Message Added", {
            "thread_id": thread_id,
            "message_type": message_type,
            "message_length": len(message)
        })
        
        return True
    except Exception as e:
        agent_logger.error(f"❌ Error adding system message: {e}")
        log_agent_flow("SYSTEM", "System Message Failed", {"error": str(e)})
        return False


def get_conversation_state(
    conversation_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    phone_number: Optional[str] = None
) -> Optional[dict]:
    """Get current conversation state from checkpointer.
    
    Args:
        conversation_id: Optional conversation ID
        customer_id: Optional customer ID
        phone_number: Optional phone number
    
    Returns:
        dict: Current state values, or None if error or no state exists
    """
    try:
        thread_id = get_thread_id(conversation_id, customer_id, phone_number)
        config = get_config(thread_id)
        
        current_state = receptionist_graph.get_state(config)
        return current_state.values if current_state.values else None
    except Exception as e:
        agent_logger.warning(f"⚠️ Error getting conversation state: {e}")
        return None
