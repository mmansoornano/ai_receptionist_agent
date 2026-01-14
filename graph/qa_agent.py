"""Q&A agent for handling general questions."""
import time
from langchain_core.messages import SystemMessage
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.database_tool import get_customer
from tools.calendar_tool import list_upcoming_events
from tools.rag_tool import search_knowledge_base
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call

QA_TOOLS = [search_knowledge_base, get_customer, list_upcoming_events]

QA_SYSTEM_PROMPT = """You are an AI receptionist that answers general questions about the business.

You can help with:
- Opening hours
- Services offered
- General business information
- Contact information
- Status of existing appointments

Be friendly, professional, and helpful. Always respond to customers in English.

If you don't know the answer, be honest and offer to connect the customer to a human."""


def qa_agent(state: ReceptionistState) -> ReceptionistState:
    """Q&A agent that handles general questions."""
    log_agent_flow("QA", "Agent Invoked", {
        "tools_count": len(QA_TOOLS) if QA_TOOLS else 0,
        "tools": [tool.name for tool in QA_TOOLS] if QA_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Create system message
    system_msg = SystemMessage(content=QA_SYSTEM_PROMPT)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and QA_TOOLS:
        llm_with_tools = llm.bind_tools(QA_TOOLS)
        log_agent_flow("QA", "LLM with Tools", {"tools_bound": True})
    else:
        llm_with_tools = llm
        log_agent_flow("QA", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM
    log_llm_call(llm_service.provider_name, llm_service.model_name, "QA Agent")
    response = llm_with_tools.invoke(agent_messages)
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "QA Agent", response_time)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("QA", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
qa_tool_node = ToolNode(QA_TOOLS) if QA_TOOLS else None
