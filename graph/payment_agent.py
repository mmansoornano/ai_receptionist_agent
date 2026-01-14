"""Payment agent for handling Easypaisa payment flow."""
import time
from langchain_core.messages import SystemMessage
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.payment_tool import PAYMENT_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call

PAYMENT_SYSTEM_PROMPT = """You are an AI assistant for a protein bar company that helps customers complete payments via Easypaisa.

Payment Flow:
1. Request the customer's mobile number
2. Send OTP to the mobile number using send_payment_otp tool
3. Request the OTP from the customer
4. Verify the OTP using verify_payment_otp tool
5. Confirm payment using confirm_easypaisa_payment tool with the amount
6. Create order using create_order_from_cart tool with cart data and transaction ID

Be friendly, professional, and helpful. Always respond to customers in English.
Guide customers through the payment process step by step.
Confirm each step clearly."""


def payment_agent(state: ReceptionistState) -> ReceptionistState:
    """Payment agent that handles Easypaisa payment flow."""
    log_agent_flow("PAYMENT", "Agent Invoked", {
        "tools_count": len(PAYMENT_TOOLS) if PAYMENT_TOOLS else 0,
        "tools": [tool.name for tool in PAYMENT_TOOLS] if PAYMENT_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Create system message
    system_msg = SystemMessage(content=PAYMENT_SYSTEM_PROMPT)
    
    # Prepare messages with system prompt
    agent_messages = [system_msg] + messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and PAYMENT_TOOLS:
        llm_with_tools = llm.bind_tools(PAYMENT_TOOLS)
        log_agent_flow("PAYMENT", "LLM with Tools", {"tools_bound": True})
    else:
        llm_with_tools = llm
        log_agent_flow("PAYMENT", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Payment Agent")
    response = llm_with_tools.invoke(agent_messages)
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Payment Agent", response_time)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("PAYMENT", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
payment_tool_node = ToolNode(PAYMENT_TOOLS) if PAYMENT_TOOLS else None
