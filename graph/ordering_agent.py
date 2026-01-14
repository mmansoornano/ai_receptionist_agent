"""Ordering agent for managing shopping cart and orders."""
import time
from langchain_core.messages import SystemMessage
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.cart_tool import CART_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call

ORDERING_SYSTEM_PROMPT = """You are an AI assistant for a protein bar company that helps customers manage their shopping cart and place orders.

You can help with:
- Adding products to the cart
- Viewing cart contents
- Updating quantities
- Removing items from cart
- Clearing the cart

When customers want to add items, use the add_item_to_cart tool with the product_id.
When customers want to see their cart, use the view_cart tool.
When customers want to modify quantities, use the update_cart_quantity tool.
When customers want to remove items, use the remove_item_from_cart tool.

Be friendly, professional, and helpful. Always respond to customers in English.
Confirm actions clearly and show cart totals when relevant."""


def ordering_agent(state: ReceptionistState) -> ReceptionistState:
    """Ordering agent that handles cart management."""
    log_agent_flow("ORDERING", "Agent Invoked", {
        "tools_count": len(CART_TOOLS) if CART_TOOLS else 0,
        "tools": [tool.name for tool in CART_TOOLS] if CART_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Create system message
    system_msg = SystemMessage(content=ORDERING_SYSTEM_PROMPT)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and CART_TOOLS:
        llm_with_tools = llm.bind_tools(CART_TOOLS)
        log_agent_flow("ORDERING", "LLM with Tools", {"tools_bound": True})
    else:
        llm_with_tools = llm
        log_agent_flow("ORDERING", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent")
    response = llm_with_tools.invoke(agent_messages)
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent", response_time)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("ORDERING", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
ordering_tool_node = ToolNode(CART_TOOLS) if CART_TOOLS else None
