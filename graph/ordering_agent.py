"""Ordering agent for managing shopping cart and orders."""
import time
from langchain_core.messages import SystemMessage, ToolMessage
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from tools.cart_tool import CART_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call


def ordering_agent(state: ReceptionistState) -> ReceptionistState:
    """Ordering agent that handles cart management."""
    log_agent_flow("ORDERING", "Agent Invoked", {
        "tools_count": len(CART_TOOLS) if CART_TOOLS else 0,
        "tools": [tool.name for tool in CART_TOOLS] if CART_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Get prompt and create system message
    ordering_prompt = get_prompt("ordering_agent")
    customer_id = state.get("customer_id")
    if customer_id:
        ordering_prompt += f"\n\nCustomer ID: {customer_id}\nAlways pass this customer_id to cart or address tools."
    system_msg = SystemMessage(content=ordering_prompt)
    
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
            
            # If this is a cart-related tool and customer_id is available, inject it
            if customer_id and tool_name in ['add_item_to_cart', 'view_cart', 'update_cart_quantity', 'remove_item_from_cart', 'clear_shopping_cart']:
                if 'customer_id' not in tool_args or tool_args.get('customer_id') == 'anonymous':
                    tool_args['customer_id'] = customer_id
                    modified = True
                    log_agent_flow("ORDERING", "Injected customer_id into tool call", {
                        "tool": tool_name,
                        "customer_id": customer_id
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


# Create custom tool node that injects customer_id
ordering_tool_node = OrderingToolNodeWithState(CART_TOOLS) if CART_TOOLS else None
