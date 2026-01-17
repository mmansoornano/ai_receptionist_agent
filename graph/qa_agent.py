"""Q&A agent for handling general questions."""
import time
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
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
from utils.logger import log_agent_flow, log_llm_call

QA_TOOLS = [search_knowledge_base, get_customer, list_upcoming_events] + PRODUCT_TOOLS + CALCULATOR_TOOLS


def qa_agent(state: ReceptionistState) -> ReceptionistState:
    """Q&A agent that handles general questions and product inquiries."""
    intent = state.get("intent", "general_qa")
    
    log_agent_flow("QA", "Agent Invoked", {
        "intent": intent,
        "tools_count": len(QA_TOOLS) if QA_TOOLS else 0,
        "tools": [tool.name for tool in QA_TOOLS] if QA_TOOLS else []
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Get prompt and create system message
    qa_prompt = get_prompt("qa_agent")
    
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
    
    system_msg = SystemMessage(content=qa_prompt)
    
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
    
    # Add response to messages
    new_messages = messages + [response]
    
    return {**state, "messages": new_messages}


# Create tool node for executing tools
qa_tool_node = ToolNode(QA_TOOLS) if QA_TOOLS else None
