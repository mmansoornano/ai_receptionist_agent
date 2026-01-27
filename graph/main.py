"""Main LangGraph graph orchestration."""
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from graph.state import ReceptionistState
from graph.router import router_agent
from graph.qa_agent import qa_agent, qa_tool_node
from graph.ordering_agent import ordering_agent, ordering_tool_node
from graph.payment_agent import payment_agent, payment_tool_node
from graph.cancellation_agent import cancellation_agent, cancellation_tool_node


def call_tools(state: ReceptionistState) -> Command | ReceptionistState:
    """Route to appropriate tool node based on intent."""
    from utils.logger import log_agent_flow, log_graph_flow
    
    log_graph_flow("tools", "Entering Node")
    
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
    
    # Preserve active_agent and intent from original state (tool nodes don't preserve them)
    active_agent = state.get("active_agent")
    original_intent = state.get("intent", intent)
    
    result_state = state
    if intent == "ordering" and ordering_tool_node:
        result_state = ordering_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Ordering Tools Executed")
    elif intent == "payment" and payment_tool_node:
        result_state = payment_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Payment Tools Executed")
    elif intent == "cancellation" and cancellation_tool_node:
        result_state = cancellation_tool_node.invoke(state)
        log_agent_flow("TOOLS", "Cancellation Tools Executed")
    elif (intent == "product_inquiry" or intent == "general_qa") and qa_tool_node:
        result_state = qa_tool_node.invoke(state)
        log_agent_flow("TOOLS", "QA Tools Executed")
    else:
        # No tools to execute
        log_agent_flow("TOOLS", "No Tools to Execute")
    
    # Preserve active_agent and intent in result_state (tool nodes only return messages)
    if active_agent or original_intent:
        result_state = {
            **result_state,
            "active_agent": active_agent or result_state.get("active_agent"),
            "intent": original_intent or result_state.get("intent", intent)
        }
    
    log_graph_flow("tools", "Exiting Node", {"intent": intent})
    
    # #region debug log
    import json
    import time
    try:
        with open("/Users/home/Documents/Convsol/Agent/AI Receptionist/AI_receptionist_agent/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:53","message":"AFTER tools - routing decision","data":{"active_agent_from_state":result_state.get("active_agent"),"intent":result_state.get("intent"),"has_active_agent":bool(result_state.get("active_agent")),"original_active_agent":active_agent,"original_intent":original_intent},"timestamp":int(time.time()*1000)}) + "\n")
    except: pass
    # #endregion
    
    # Use Command to route back to the active agent after tools execute
    # CRITICAL: Include the updated messages (with ToolMessages) in the Command update
    active_agent = result_state.get("active_agent")
    if active_agent:
        # #region debug log
        try:
            with open("/Users/home/Documents/Convsol/Agent/AI Receptionist/AI_receptionist_agent/.cursor/debug.log", "a") as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:59","message":"Routing via active_agent","data":{"active_agent":active_agent},"timestamp":int(time.time()*1000)}) + "\n")
        except: pass
        # #endregion
        # Include messages update so ToolMessages are preserved
        return Command(
            update={"messages": result_state.get("messages", [])},
            goto=active_agent
        )
    
    # Fallback routing based on intent
    intent = result_state.get("intent", "general_qa")
    agent_mapping = {
        "ordering": "ordering_agent",
        "payment": "payment_agent",
        "cancellation": "cancellation_agent"
    }
    next_agent = agent_mapping.get(intent, "qa_agent")
    
    # #region debug log
    try:
        with open("/Users/home/Documents/Convsol/Agent/AI Receptionist/AI_receptionist_agent/.cursor/debug.log", "a") as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"main.py:70","message":"Fallback routing via intent","data":{"intent":intent,"next_agent":next_agent},"timestamp":int(time.time()*1000)}) + "\n")
    except: pass
    # #endregion
    
    # Include messages update so ToolMessages are preserved
    return Command(
        update={"messages": result_state.get("messages", [])},
        goto=next_agent
    )


def create_receptionist_graph():
    """Create the main receptionist graph."""
    # Create graph
    workflow = StateGraph(ReceptionistState)
    
    # Add nodes - with Command, nodes can specify next node dynamically
    # The actual routing is handled by Command returns from nodes
    # Visualization will automatically show destinations based on Command returns
    workflow.add_node("router", router_agent)
    workflow.add_node("qa_agent", qa_agent)
    workflow.add_node("ordering_agent", ordering_agent)
    workflow.add_node("payment_agent", payment_agent)
    workflow.add_node("cancellation_agent", cancellation_agent)
    workflow.add_node("tools", call_tools)
    
    # Add initial entry point - only edge needed since Command handles all other routing
    workflow.add_edge(START, "router")
    
    # Compile graph with checkpointer for state persistence between API calls
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)


# Create the graph instance
receptionist_graph = create_receptionist_graph()
