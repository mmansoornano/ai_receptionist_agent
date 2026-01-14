"""Cancellation agent for handling order cancellations."""
import time
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from tools.cancellation_tool import CANCELLATION_TOOLS
from utils.logger import log_agent_flow, log_llm_call


def cancellation_agent(state: ReceptionistState) -> ReceptionistState:
    """Cancellation agent that handles order cancellations."""
    log_agent_flow("CANCELLATION", "Agent Invoked", {
        "tools_count": len(CANCELLATION_TOOLS) if CANCELLATION_TOOLS else 0,
        "tools": [tool.name for tool in CANCELLATION_TOOLS] if CANCELLATION_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Get prompt and create system message
    cancellation_prompt = get_prompt("cancellation_agent")
    system_msg = SystemMessage(content=cancellation_prompt)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and CANCELLATION_TOOLS:
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
cancellation_tool_node = ToolNode(CANCELLATION_TOOLS) if CANCELLATION_TOOLS else None
