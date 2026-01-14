"""Q&A agent for handling general questions."""
import time
from langchain_core.messages import SystemMessage
from config import DEFAULT_LANGUAGE
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from tools.database_tool import get_customer
from tools.calendar_tool import list_upcoming_events
from tools.rag_tool import search_knowledge_base
from tools.product_tool import PRODUCT_TOOLS
from tools.calculator_tool import CALCULATOR_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call

QA_TOOLS = [search_knowledge_base, get_customer, list_upcoming_events] + PRODUCT_TOOLS + CALCULATOR_TOOLS

QA_SYSTEM_PROMPT = """You are an AI assistant for a protein bar company that answers product questions and helps customers.

You can help with:
- Product information (protein bars, granola bars, cookies, cereals, gift boxes)
- Product prices and pricing information (all prices are in PKR - Pakistani Rupees)
- Product features, ingredients, and specifications
- Product categories and options
- Special offers and promotions

When users ask "what products do you have" or "show me all products", use the list_all_products tool to show all available products with their prices.

When calculating prices or totals, use the calculate_price tool to add up prices accurately.

Be friendly, professional, and helpful. Always respond to customers in English.
When answering product questions, refer to "our products" or "protein bars" rather than specific brand names.
Use the search_knowledge_base tool to find detailed product information.
Always show prices in PKR (Pakistani Rupees) format.

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
