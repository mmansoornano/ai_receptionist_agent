"""Booking agent for handling appointment bookings."""
import time
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import ToolNode
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.calendar_tool import CALENDAR_TOOLS
from tools.database_tool import DATABASE_TOOLS
from tools.notification_tool import NOTIFICATION_TOOLS
from utils.logger import log_agent_flow, log_llm_call

# Combine all tools for booking agent
BOOKING_TOOLS = CALENDAR_TOOLS + DATABASE_TOOLS + [NOTIFICATION_TOOLS[2]]  # Include send_booking_confirmation

BOOKING_SYSTEM_PROMPT = """You are an AI receptionist that helps customers book appointments.

Your tasks:
1. Greet customers politely in English
2. Collect necessary information:
   - Customer name
   - Phone number (if not already known)
   - Email (optional)
   - Desired date and time
   - Service type
3. Check availability in the calendar
4. Create the appointment in the calendar and database
5. Send confirmation via email and SMS

Be friendly, professional, and helpful. Always respond to customers in English."""


def booking_agent(state: ReceptionistState) -> ReceptionistState:
    """Booking agent that handles appointment bookings."""
    log_agent_flow("BOOKING", "Agent Invoked", {
        "tools_count": len(BOOKING_TOOLS),
        "tools": [tool.name for tool in BOOKING_TOOLS]
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Create system message
    system_msg = SystemMessage(content=BOOKING_SYSTEM_PROMPT)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported)
    if llm_service.supports_tools():
        llm_with_tools = llm.bind_tools(BOOKING_TOOLS)
        log_agent_flow("BOOKING", "LLM with Tools", {"tools_bound": True})
    else:
        llm_with_tools = llm
        log_agent_flow("BOOKING", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Booking Agent")
    response = llm_with_tools.invoke(agent_messages)
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Booking Agent", response_time)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("BOOKING", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
booking_tool_node = ToolNode(BOOKING_TOOLS)
