"""LangGraph state definition for the receptionist agent system."""
from typing import Annotated, Optional, Dict, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ReceptionistState(TypedDict):
    """State for the receptionist multi-agent system.
    
    The messages field uses add_messages reducer which:
    - APPENDS new messages to existing ones (does not replace)
    - PRESERVES all messages from start of conversation
    - Accumulates both HumanMessage and AIMessage throughout execution
    - When nodes return {"messages": [new_msg]}, reducer appends to existing list
    - Result: [msg1, msg2, ..., new_msg] - all messages preserved
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    intent: Optional[str]  # "product_inquiry", "ordering", "payment", "cancellation", "general_qa"
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
