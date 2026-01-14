"""Router agent for intent classification."""
import time
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from utils.logger import log_agent_flow, log_intent_classification, log_llm_call


ROUTER_SYSTEM_PROMPT = """You are an AI assistant that classifies user intent for a protein bar company chatbot.

Analyze the user's message and determine the intent:
- "product_inquiry": User is asking about products, prices, features, specifications, or product information
- "ordering": User wants to add items to cart, view cart, update quantities, remove items, or manage shopping cart
- "payment": User wants to make a payment, checkout, or complete a purchase
- "cancellation": User wants to cancel an order or get refund/reimbursement information
- "general_qa": User is asking general questions (anything else)

Respond ONLY with one of these five words: product_inquiry, ordering, payment, cancellation, or general_qa.
No other text."""


def router_agent(state: ReceptionistState) -> ReceptionistState:
    """Router agent that classifies user intent."""
    log_agent_flow("ROUTER", "Starting Intent Classification")
    
    messages = state.get("messages", [])
    if not messages:
        log_intent_classification("general_qa", "default (no messages)")
        return {**state, "intent": "general_qa"}
    
    # Get the last user message
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        log_intent_classification("general_qa", "default (not HumanMessage)")
        return {**state, "intent": "general_qa"}
    
    # Use LLM to classify intent
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0)
    
    classification_prompt = f"{ROUTER_SYSTEM_PROMPT}\n\nUser message: {last_message.content}"
    
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Intent Classification")
    response = llm.invoke([HumanMessage(content=classification_prompt)])
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Intent Classification", response_time)
    
    intent = response.content.strip().lower()
    
    # Validate intent
    valid_intents = ["product_inquiry", "ordering", "payment", "cancellation", "general_qa"]
    if intent not in valid_intents:
        log_intent_classification("general_qa", f"default (invalid: {intent})")
        intent = "general_qa"  # Default to general_qa if unclear
    else:
        log_intent_classification(intent, "valid")
    
    log_agent_flow("ROUTER", "Intent Classification Complete", {"intent": intent})
    return {**state, "intent": intent}


def route_to_agent(state: ReceptionistState) -> Literal["qa_agent", "ordering_agent", "payment_agent", "cancellation_agent"]:
    """Route to appropriate agent based on intent."""
    intent = state.get("intent", "general_qa")
    
    if intent == "product_inquiry" or intent == "general_qa":
        log_agent_flow("ROUTER", "Routing to QA Agent")
        return "qa_agent"
    elif intent == "ordering":
        log_agent_flow("ROUTER", "Routing to Ordering Agent")
        return "ordering_agent"
    elif intent == "payment":
        log_agent_flow("ROUTER", "Routing to Payment Agent")
        return "payment_agent"
    elif intent == "cancellation":
        log_agent_flow("ROUTER", "Routing to Cancellation Agent")
        return "cancellation_agent"
    else:
        log_agent_flow("ROUTER", "Routing to QA Agent (default)")
        return "qa_agent"
