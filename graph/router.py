"""Router agent for intent classification."""
import time
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from services.llm_service import get_llm_service
from graph.state import ReceptionistState
from utils.logger import log_agent_flow, log_intent_classification, log_llm_call


ROUTER_SYSTEM_PROMPT = """You are an AI receptionist that classifies user intent.

Analyze the user's message and determine the intent:
- "booking": User wants to book an appointment
- "cancellation": User wants to cancel an appointment
- "question": User is asking a general question

Respond ONLY with one of these three words: booking, cancellation, or question.
No other text."""


def router_agent(state: ReceptionistState) -> ReceptionistState:
    """Router agent that classifies user intent."""
    log_agent_flow("ROUTER", "Starting Intent Classification")
    
    messages = state.get("messages", [])
    if not messages:
        log_intent_classification("question", "default (no messages)")
        return {**state, "intent": "question"}
    
    # Get the last user message
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        log_intent_classification("question", "default (not HumanMessage)")
        return {**state, "intent": "question"}
    
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
    if intent not in ["booking", "cancellation", "question"]:
        log_intent_classification("question", f"default (invalid: {intent})")
        intent = "question"  # Default to question if unclear
    else:
        log_intent_classification(intent, "valid")
    
    log_agent_flow("ROUTER", "Intent Classification Complete", {"intent": intent})
    return {**state, "intent": intent}


def route_to_agent(state: ReceptionistState) -> Literal["booking_agent", "qa_agent", "cancellation_agent"]:
    """Route to appropriate agent based on intent."""
    intent = state.get("intent", "question")
    
    if intent == "booking":
        log_agent_flow("ROUTER", "Routing to Booking Agent")
        return "booking_agent"
    elif intent == "cancellation":
        log_agent_flow("ROUTER", "Routing to Cancellation Agent")
        return "cancellation_agent"
    else:
        log_agent_flow("ROUTER", "Routing to QA Agent")
        return "qa_agent"
