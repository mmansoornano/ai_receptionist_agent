"""Q&A agent for handling general questions."""
import time
import json
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from tools.database_tool import get_customer
from tools.calendar_tool import list_upcoming_events
from tools.rag_tool import search_knowledge_base
from tools.product_tool import PRODUCT_TOOLS
from tools.calculator_tool import CALCULATOR_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call, log_prompt, log_graph_flow
from utils.conversation_history import format_conversation_history
from utils.message_utils import create_message_update_command
from utils.message_filtering import filter_messages_for_agent, get_last_human_message
from utils.llm_retry import invoke_with_retry
from utils.error_handler import handle_llm_error

QA_TOOLS = [search_knowledge_base, get_customer, list_upcoming_events] + PRODUCT_TOOLS + CALCULATOR_TOOLS


def qa_agent(state: ReceptionistState) -> Command | ReceptionistState:
    """Q&A agent that handles general questions and product inquiries."""
    log_graph_flow("qa_agent", "Entering Node")
    intent = state.get("intent", "general_qa")
    
    log_agent_flow("QA", "Agent Invoked", {
        "intent": intent,
        "tools_count": len(QA_TOOLS) if QA_TOOLS else 0,
        "tools": [tool.name for tool in QA_TOOLS] if QA_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # ToolMessages must stay paired with any AIMessage that has tool_calls (OpenAI Chat API rule).
    filtered_messages = filter_messages_for_agent(messages, include_system=True, include_tool_results=True)
    last_human_message = get_last_human_message(messages)
    
    # Get prompt and create system message
    qa_prompt = get_prompt("qa_agent")
    
    # Trim messages for token limits AFTER filtering (matches what LLM will see)
    # Strategy: keep most recent messages, ensuring we have human messages for context
    # Remove end_on to preserve AIMessages with tool calls (end_on excludes them)
    trimmed_messages = trim_messages(
        filtered_messages,  # Use filtered messages instead of raw messages
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=3000,  # Keep recent messages within token limit
        start_on="human",
        include_system=False,  # We add system message separately
        allow_partial=False
    )
    
    # Format conversation history from FULL messages in state (not trimmed)
    # This ensures we can show the last 10 conversation messages, even if trim_messages
    # limits tokens and only keeps a few messages for the LLM call
    # Trimmed messages are used for the LLM call, but history uses full messages
    conversation_history = format_conversation_history(messages, max_messages=10)  # Use full messages for history
    if conversation_history:
        # Count actual messages in history (each line represents one message exchange)
        history_line_count = len(conversation_history.split("\n")) if conversation_history else 0
        qa_prompt += f"\n\nCONVERSATION HISTORY (last {history_line_count} messages):\n{conversation_history}\n\nUse this conversation history to understand context and provide relevant responses."
    
    # Enhance prompt for product inquiries to prioritize product tools
    tool_result_content = None
    has_tool_results = False
    
    if intent == "product_inquiry":
        # Check if tool results are already in messages (after tool execution)
        # ToolMessage objects contain tool results
        has_tool_results = any(
            isinstance(msg, ToolMessage) and 
            hasattr(msg, 'content') and 
            msg.content and 
            ('PRODUCT CATALOG' in str(msg.content) or 'PKR' in str(msg.content))
            for msg in messages
        )
        
        if has_tool_results:
            # Tool has been executed, emphasize using the results
            # Find the tool result message
            for msg in messages:
                if isinstance(msg, ToolMessage) and hasattr(msg, 'content') and msg.content:
                    content_str = str(msg.content)
                    if 'PRODUCT CATALOG' in content_str or 'PKR' in content_str:
                        tool_result_content = content_str
                        break
            
            qa_prompt += f"\n\nCRITICAL: This is a PRODUCT INQUIRY. The list_all_products tool has been executed and product data with prices is available in the conversation history above. You MUST read the tool results (ToolMessage) and present ALL product prices directly to the user. Do NOT ask clarifying questions. Do NOT offer other services. Simply present the product catalog with prices as shown in the tool results. The user asked for prices - provide them now."
        else:
            # Tool hasn't been called yet, instruct to call it
            qa_prompt += "\n\nIMPORTANT: This is a PRODUCT INQUIRY. You MUST use the list_all_products tool to fetch live product data from the backend. Do not rely solely on knowledge base - always use the list_all_products tool when users ask about products, prices, or product availability."
    
    # Log the prompt being used
    log_prompt("QA_AGENT", qa_prompt, {
        "intent": intent,
        "has_tool_results": has_tool_results,
        "message_count": len(messages)
    })
    
    system_msg = SystemMessage(content=qa_prompt)
    
    # Prepare messages with system prompt (trimmed messages already processed above)
    # Full message history remains in state - trimmed_messages are only for LLM context
    agent_messages = [system_msg] + trimmed_messages
    
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
    
    # Get response from LLM with retry logic
    log_llm_call(llm_service.provider_name, llm_service.model_name, "QA Agent")
    try:
        response = invoke_with_retry(
            llm=llm_with_tools,
            messages=agent_messages,
            max_retries=3,
            initial_delay=1.0,
            agent_name="qa_agent"
        )
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "QA Agent", response_time)
    except Exception as e:
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "QA Agent", response_time)
        return handle_llm_error(e, "qa_agent", state)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("QA", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    # For product inquiries with tool results, ensure the product catalog is included in response
    if intent == "product_inquiry" and has_tool_results and tool_result_content:
        # Check if the response already contains the product catalog
        response_content = response.content if hasattr(response, 'content') and response.content else ""
        if 'PRODUCT CATALOG' not in response_content and tool_result_content:
            # The LLM didn't include the catalog, so we'll prepend it
            enhanced_content = f"{tool_result_content}\n\n{response_content}" if response_content else tool_result_content
            response = AIMessage(
                content=enhanced_content,
                tool_calls=getattr(response, 'tool_calls', None),
                id=getattr(response, 'id', None)
            )
            log_agent_flow("QA", "Enhanced response with product catalog", {"catalog_included": True})
    
    log_graph_flow("qa_agent", "Exiting Node", {"has_tool_calls": bool(hasattr(response, 'tool_calls') and response.tool_calls)})
    
    # Use Command for dynamic routing: if tool calls exist, go to tools, otherwise end
    # add_messages reducer will APPEND response to existing messages, preserving ALL old messages
    has_tool_calls = hasattr(response, 'tool_calls') and response.tool_calls
    next_node = "tools" if has_tool_calls else "__end__"
    
    # Pass state to log existing message count - reducer will append new message to existing ones
    return create_message_update_command(
        [response],
        state=state,
        goto=next_node,
        active_agent="qa_agent"
    )


# Create tool node for executing tools
qa_tool_node = ToolNode(QA_TOOLS) if QA_TOOLS else None
