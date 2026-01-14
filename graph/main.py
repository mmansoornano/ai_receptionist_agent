"""Main LangGraph graph orchestration."""
from langgraph.graph import StateGraph, START, END
from graph.state import ReceptionistState
from graph.router import router_agent, route_to_agent
from graph.qa_agent import qa_agent, qa_tool_node
from graph.ordering_agent import ordering_agent, ordering_tool_node
from graph.payment_agent import payment_agent, payment_tool_node
from graph.cancellation_agent import cancellation_agent, cancellation_tool_node
from langchain_core.messages import AIMessage


def should_continue(state: ReceptionistState) -> str:
    """Determine if we should continue or end."""
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    
    # If last message has tool calls, execute tools
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end conversation
    return "end"


def call_tools(state: ReceptionistState) -> ReceptionistState:
    """Route to appropriate tool node based on intent."""
    from utils.logger import log_agent_flow
    
    intent = state.get("intent", "general_qa")
    messages = state.get("messages", [])
    
    # Check for tool calls in last message
    last_message = messages[-1] if messages else None
    tool_calls = []
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        tool_calls = [tc.get('name', 'unknown') for tc in last_message.tool_calls]
    
    log_agent_flow("TOOLS", "Executing Tools", {
        "intent": intent,
        "tool_count": len(tool_calls),
        "tools": tool_calls
    })
    
    if intent == "ordering" and ordering_tool_node:
        result = ordering_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Ordering Tools Executed")
        return result
    elif intent == "payment" and payment_tool_node:
        result = payment_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Payment Tools Executed")
        return result
    elif intent == "cancellation" and cancellation_tool_node:
        result = cancellation_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Cancellation Tools Executed")
        return result
    elif (intent == "product_inquiry" or intent == "general_qa") and qa_tool_node:
        result = qa_tool_node.invoke(state)
        log_agent_flow("TOOLS", "QA Tools Executed")
        return result
    else:
        # No tools to execute
        log_agent_flow("TOOLS", "No Tools to Execute")
        return state


def create_receptionist_graph():
    """Create the main receptionist graph."""
    # Create graph
    workflow = StateGraph(ReceptionistState)
    
    # Add nodes
    workflow.add_node("router", router_agent)
    workflow.add_node("qa_agent", qa_agent)
    workflow.add_node("ordering_agent", ordering_agent)
    workflow.add_node("payment_agent", payment_agent)
    workflow.add_node("cancellation_agent", cancellation_agent)
    workflow.add_node("tools", call_tools)
    
    # Add edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "qa_agent": "qa_agent",
            "ordering_agent": "ordering_agent",
            "payment_agent": "payment_agent",
            "cancellation_agent": "cancellation_agent",
        }
    )
    
    # Add conditional edges for each agent
    for agent_name in ["qa_agent", "ordering_agent", "payment_agent", "cancellation_agent"]:
        workflow.add_conditional_edges(
            agent_name,
            should_continue,
            {
                "tools": "tools",
                "end": END,
            }
        )
    
    # After tools, continue back to the agent
    def route_after_tools(state: ReceptionistState) -> str:
        """Route back to agent after tools."""
        intent = state.get("intent", "general_qa")
        if intent == "ordering":
            return "ordering_agent"
        elif intent == "payment":
            return "payment_agent"
        elif intent == "cancellation":
            return "cancellation_agent"
        else:
            return "qa_agent"
    
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "qa_agent": "qa_agent",
            "ordering_agent": "ordering_agent",
            "payment_agent": "payment_agent",
            "cancellation_agent": "cancellation_agent",
        }
    )
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
receptionist_graph = create_receptionist_graph()
