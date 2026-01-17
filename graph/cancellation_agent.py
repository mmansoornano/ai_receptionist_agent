"""Cancellation agent for handling order cancellations."""
import time
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from tools.cancellation_tool import CANCELLATION_TOOLS
from utils.logger import log_agent_flow, log_llm_call, log_prompt, log_graph_flow
from utils.conversation_history import format_conversation_history
from utils.message_utils import create_message_update_command


def cancellation_agent(state: ReceptionistState) -> Command | ReceptionistState:
    """Cancellation agent that handles order cancellations."""
    log_graph_flow("cancellation_agent", "Entering Node")
    log_agent_flow("CANCELLATION", "Agent Invoked", {
        "tools_count": len(CANCELLATION_TOOLS) if CANCELLATION_TOOLS else 0,
        "tools": [tool.name for tool in CANCELLATION_TOOLS] if CANCELLATION_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Get prompt and create system message
    cancellation_prompt = get_prompt("cancellation_agent")
    
    # Trim messages for token limits BEFORE formatting history (matches what LLM will see)
    # Remove end_on to preserve AIMessages with tool calls (end_on excludes them)
    trimmed_messages = trim_messages(
        messages,
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=3000,
        start_on="human",
        include_system=False,
        allow_partial=False
    )
    
    # Format conversation history from FULL messages in state (not trimmed)
    # This ensures we can show the last 10 conversation messages, even if trim_messages
    # limits tokens and only keeps a few messages for the LLM call
    conversation_history = format_conversation_history(messages, max_messages=10)  # Use full messages for history
    if conversation_history:
        # Count actual messages in history (each line represents one message exchange)
        history_line_count = len(conversation_history.split("\n")) if conversation_history else 0
        cancellation_prompt += f"\n\nCONVERSATION HISTORY (last {history_line_count} messages):\n{conversation_history}\n\nUse this conversation history to understand the order context and cancellation request."
    
    # Log the prompt being used
    log_prompt("CANCELLATION_AGENT", cancellation_prompt, {
        "message_count": len(messages)
    })
    
    system_msg = SystemMessage(content=cancellation_prompt)
    
    # Prepare messages with system prompt (trimmed messages already processed above)
    # Full message history remains in state - trimmed_messages are only for LLM context
    agent_messages = [system_msg] + trimmed_messages
    
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
    
    has_tool_calls = bool(hasattr(response, 'tool_calls') and response.tool_calls)
    log_graph_flow("cancellation_agent", "Exiting Node", {"has_tool_calls": has_tool_calls})
    
    # Use Command for dynamic routing: if tool calls exist, go to tools, otherwise end
    # add_messages reducer will APPEND response to existing messages, preserving ALL old messages
    next_node = "tools" if has_tool_calls else "__end__"
    
    return create_message_update_command(
        [response],
        state=state,
        goto=next_node
    )


# Create tool node for executing tools
cancellation_tool_node = ToolNode(CANCELLATION_TOOLS) if CANCELLATION_TOOLS else None
