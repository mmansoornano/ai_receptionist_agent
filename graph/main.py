"""Main LangGraph graph orchestration."""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from graph.state import ReceptionistState
from graph.router import router_agent, route_to_agent
from graph.booking_agent import booking_agent, booking_tool_node
from graph.qa_agent import qa_agent, qa_tool_node
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
    
    intent = state.get("intent", "question")
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
    
    if intent == "booking":
        result = booking_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Booking Tools Executed")
        return result
    elif intent == "cancellation":
        result = cancellation_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Cancellation Tools Executed")
        return result
    elif qa_tool_node:
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
    workflow.add_node("booking_agent", booking_agent)
    workflow.add_node("qa_agent", qa_agent)
    workflow.add_node("cancellation_agent", cancellation_agent)
    workflow.add_node("tools", call_tools)
    
    # Add edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "booking_agent": "booking_agent",
            "qa_agent": "qa_agent",
            "cancellation_agent": "cancellation_agent",
        }
    )
    
    # Add conditional edges for each agent
    for agent_name in ["booking_agent", "qa_agent", "cancellation_agent"]:
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
        intent = state.get("intent", "question")
        if intent == "booking":
            return "booking_agent"
        elif intent == "cancellation":
            return "cancellation_agent"
        else:
            return "qa_agent"
    
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "booking_agent": "booking_agent",
            "cancellation_agent": "cancellation_agent",
            "qa_agent": "qa_agent",
        }
    )
    
    # Compile graph
    return workflow.compile()


# Create the graph instance
receptionist_graph = create_receptionist_graph()
