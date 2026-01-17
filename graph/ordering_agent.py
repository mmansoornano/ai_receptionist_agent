"""Ordering agent for managing shopping cart and orders."""
import time
from langchain_core.messages import SystemMessage, ToolMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from tools.cart_tool import CART_TOOLS
from tools.product_tool import PRODUCT_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call, log_prompt, log_graph_flow
from utils.conversation_history import format_conversation_history
from utils.message_utils import create_message_update_command
from utils.message_filtering import filter_messages_for_agent, get_last_human_message
from utils.llm_retry import invoke_with_retry
from utils.error_handler import handle_llm_error


def ordering_agent(state: ReceptionistState) -> Command | ReceptionistState:
    """Ordering agent that handles cart management."""
    from langchain_core.messages import HumanMessage
    
    log_graph_flow("ordering_agent", "Entering Node")
    # Combine cart tools and product tools for ordering agent
    ORDERING_TOOLS = (CART_TOOLS or []) + (PRODUCT_TOOLS or [])
    
    log_agent_flow("ORDERING", "Agent Invoked", {
        "tools_count": len(ORDERING_TOOLS),
        "tools": [tool.name for tool in ORDERING_TOOLS]
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Filter messages before processing (excludes ToolMessages and SystemMessages by default)
    filtered_messages = filter_messages_for_agent(messages, include_system=False, include_tool_results=False)
    last_human_message = get_last_human_message(messages)
    
    # Check if user message indicates completion/finalization (dynamic intent detection)
    # If so, update intent to "payment" for direct transition
    current_intent = state.get("intent", "ordering")
    if last_human_message:
        msg_lower = last_human_message.content.lower() if last_human_message.content else ""
        completion_phrases = ["thats all", "that's all", "finalize", "finalise", "complete", "done", "ready", "let's finalize", "lets finalize", "finalize the order", "no i don't want to add", "no more"]
        has_cart_context = any(word in " ".join([str(m.content) for m in messages[-10:]]).lower() for word in ["cart", "order", "add", "item"])
        
        if has_cart_context and any(phrase in msg_lower for phrase in completion_phrases):
            # Update intent to payment for direct transition
            current_intent = "payment"
            log_agent_flow("ORDERING", "Intent transition detected: ordering -> payment", {"trigger": msg_lower})
    
    # Get prompt and create system message
    ordering_prompt = get_prompt("ordering_agent")
    
    # Trim messages for token limits AFTER filtering (matches what LLM will see)
    # Remove end_on to preserve AIMessages with tool calls (end_on excludes them)
    trimmed_messages = trim_messages(
        filtered_messages,  # Use filtered messages instead of raw messages
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
        ordering_prompt += f"\n\nCONVERSATION HISTORY (last {history_line_count} messages):\n{conversation_history}\n\nUse this conversation history to understand context, interpret user responses correctly, and maintain conversation flow."
    
    customer_id = state.get("customer_id")
    
    # CRITICAL: Always use customer_id, never "anonymous"
    if customer_id:
        ordering_prompt += f"\n\nCRITICAL - Customer ID: {customer_id}\nYou MUST ALWAYS pass this exact customer_id to ALL cart tools (add_item_to_cart, view_cart, update_cart_quantity, remove_item_from_cart, clear_shopping_cart, set_delivery_address). NEVER use 'anonymous' - always use: {customer_id}"
    else:
        # Generate or use phone_number as customer_id if not provided
        # For now, use "anonymous" but log warning
        ordering_prompt += "\n\nWARNING: No customer_id in state. Using 'anonymous' - this may cause cart issues."
        log_agent_flow("ORDERING", "No customer_id in state", {"using_anonymous": True})
    
    # Log the prompt being used
    log_prompt("ORDERING_AGENT", ordering_prompt, {
        "customer_id": customer_id,
        "current_intent": current_intent,
        "message_count": len(messages)
    })
    
    system_msg = SystemMessage(content=ordering_prompt)
    
    # Prepare messages with system prompt (trimmed messages already processed above)
    # Full message history remains in state - trimmed_messages are only for LLM context
    agent_messages = [system_msg] + trimmed_messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and ORDERING_TOOLS:
        llm_with_tools = llm.bind_tools(ORDERING_TOOLS)
        log_agent_flow("ORDERING", "LLM with Tools", {"tools_bound": True, "tools": [tool.name for tool in ORDERING_TOOLS]})
    else:
        llm_with_tools = llm
        log_agent_flow("ORDERING", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM with retry logic
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent")
    try:
        response = invoke_with_retry(
            llm=llm_with_tools,
            messages=agent_messages,
            max_retries=3,
            initial_delay=1.0,
            agent_name="ordering_agent"
        )
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent", response_time)
    except Exception as e:
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent", response_time)
        return handle_llm_error(e, "ordering_agent", state)
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        log_agent_flow("ORDERING", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') for tc in response.tool_calls]
        })
    
    has_tool_calls = bool(hasattr(response, 'tool_calls') and response.tool_calls)
    log_graph_flow("ordering_agent", "Exiting Node", {
        "intent": current_intent,
        "has_tool_calls": has_tool_calls
    })
    
    # Use Command for dynamic routing: tools -> tools, payment intent -> payment_agent, otherwise end
    # add_messages reducer will APPEND response to existing messages, preserving ALL old messages
    if has_tool_calls:
        next_node = "tools"
    elif current_intent == "payment":
        next_node = "payment_agent"
    else:
        next_node = "__end__"
    
    return create_message_update_command(
        [response],
        state=state,
        goto=next_node,
        intent=current_intent,
        active_agent="ordering_agent"
    )


class OrderingToolNodeWithState:
    """Custom tool node that injects customer_id from state into tool calls."""
    
    def __init__(self, tools):
        self.tools = tools
        self.base_tool_node = ToolNode(tools) if tools else None
    
    def invoke(self, state: ReceptionistState) -> ReceptionistState:
        """Invoke tool node with customer_id injection."""
        from langchain_core.messages import AIMessage
        
        messages = state.get("messages", [])
        customer_id = state.get("customer_id")
        
        if not messages or not self.base_tool_node:
            return state
        
        last_message = messages[-1]
        
        # Check if last message has tool calls
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return self.base_tool_node.invoke(state)
        
        # Inject customer_id into tool calls if missing or set to "anonymous"
        modified_tool_calls = []
        modified = False
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get('name', '')
            # Handle both dict and object-style tool calls
            if isinstance(tool_call, dict):
                tool_args = tool_call.get('args', {}).copy()
                tool_id = tool_call.get('id', '')
            else:
                tool_args = getattr(tool_call, 'args', {}).copy() if hasattr(tool_call, 'args') else {}
                tool_id = getattr(tool_call, 'id', '') if hasattr(tool_call, 'id') else ''
            
            # If this is a cart-related tool and customer_id is available, ALWAYS inject it
            if customer_id and tool_name in ['add_item_to_cart', 'view_cart', 'update_cart_quantity', 'remove_item_from_cart', 'clear_shopping_cart', 'set_delivery_address']:
                # Always override customer_id to ensure consistency with state
                previous_customer_id = tool_args.get('customer_id', 'not_set')
                tool_args['customer_id'] = customer_id
                if previous_customer_id != customer_id:
                    modified = True
                    log_agent_flow("ORDERING", "Injected customer_id into tool call", {
                        "tool": tool_name,
                        "customer_id": customer_id,
                        "previous_customer_id": previous_customer_id
                    })
            
            # Reconstruct tool call
            if isinstance(tool_call, dict):
                modified_tool_calls.append({
                    **tool_call,
                    'args': tool_args
                })
            else:
                # For object-style, we need to create a dict
                modified_tool_calls.append({
                    'name': tool_name,
                    'args': tool_args,
                    'id': tool_id
                })
        
        # Create modified message with updated tool calls if needed
        if modified:
            # Create a new AIMessage with modified tool calls
            if isinstance(last_message, AIMessage):
                modified_message = AIMessage(
                    content=last_message.content,
                    tool_calls=modified_tool_calls,
                    id=getattr(last_message, 'id', None)
                )
            else:
                modified_message = AIMessage(
                    content=getattr(last_message, 'content', ''),
                    tool_calls=modified_tool_calls
                )
            modified_messages = messages[:-1] + [modified_message]
            modified_state = {**state, "messages": modified_messages}
            return self.base_tool_node.invoke(modified_state)
        
        # Execute tools using standard ToolNode
        return self.base_tool_node.invoke(state)


# Combine cart tools and product tools for tool node
ORDERING_TOOLS_FOR_NODE = (CART_TOOLS or []) + (PRODUCT_TOOLS or [])

# Create custom tool node that injects customer_id
ordering_tool_node = OrderingToolNodeWithState(ORDERING_TOOLS_FOR_NODE) if ORDERING_TOOLS_FOR_NODE else None
