"""Cancellation agent for handling appointment cancellations."""
import time
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.calendar_tool import cancel_calendar_event
from tools.database_tool import find_appointment_by_customer, cancel_appointment
from tools.notification_tool import send_cancellation_notification
from utils.logger import log_agent_flow, log_llm_call

# Combine tools for cancellation agent
CANCELLATION_TOOLS = [
    find_appointment_by_customer,
    cancel_appointment,
    cancel_calendar_event,
    send_cancellation_notification,
]

CANCELLATION_SYSTEM_PROMPT = """You are an AI receptionist that helps customers cancel appointments.

Your tasks:
1. Verify customer identity (phone number)
2. Find the customer's appointments
3. Confirm which appointment should be cancelled
4. Cancel in the calendar and database
5. Send cancellation confirmation via email and SMS

Be friendly, professional, and helpful. Always respond to customers in English."""


def cancellation_agent(state: ReceptionistState) -> ReceptionistState:
    """Cancellation agent that handles appointment cancellations."""
    log_agent_flow("CANCELLATION", "Agent Invoked", {
        "tools_count": len(CANCELLATION_TOOLS),
        "tools": [tool.name for tool in CANCELLATION_TOOLS]
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Create system message
    system_msg = SystemMessage(content=CANCELLATION_SYSTEM_PROMPT)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported)
    if llm_service.supports_tools():
        llm_with_tools = llm.bind_tools(CANCELLATION_TOOLS)
        log_agent_flow("CANCELLATION", "LLM with Tools", {"tools_bound": True})
    else:
        llm_with_tools = llm
        log_agent_flow("CANCELLATION", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Cancellation Agent")
    response = llm_with_tools.invoke(agent_messages)
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Cancellation Agent", response_time)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("CANCELLATION", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
cancellation_tool_node = ToolNode(CANCELLATION_TOOLS)
