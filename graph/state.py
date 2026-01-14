"""LangGraph state definition for the receptionist agent system."""
from typing import Annotated, Optional, Dict, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ReceptionistState(TypedDict):
    """State for the receptionist multi-agent system."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    intent: Optional[str]  # "booking", "cancellation", "question"
    customer_info: Optional[Dict]
    appointment_data: Optional[Dict]
    channel: str  # "voice" or "sms"
    language: str  # "en" (English)
    conversation_id: Optional[str]
    customer_id: Optional[str]
