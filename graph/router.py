"""Router agent for intent classification."""
import time
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from graph.state import ReceptionistState
from utils.logger import log_agent_flow, log_intent_classification, log_llm_call, log_prompt, log_graph_flow
from utils.conversation_history import format_conversation_history
from utils.message_utils import create_message_update_command


def router_agent(state: ReceptionistState) -> Command | ReceptionistState:
    """Router agent that classifies user intent using conversation history."""
    log_graph_flow("router", "Entering Node")
    log_agent_flow("ROUTER", "Starting Intent Classification")
    
    messages = state.get("messages", [])
    if not messages:
        log_intent_classification("general_qa", "default (no messages)")
        return Command(
            update={"intent": "general_qa", "conversation_context": None, "active_agent": "qa_agent"},
            goto="qa_agent"
        )
    
    # Get the last user message
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        log_intent_classification("general_qa", "default (not HumanMessage)")
        return Command(
            update={"intent": "general_qa", "conversation_context": None, "active_agent": "qa_agent"},
            goto="qa_agent"
        )
    
    # Format conversation history for context (last 10 messages)
    conversation_history = format_conversation_history(messages, max_messages=10)
    
    # Use conversation context from state if available (for efficiency)
    saved_context = state.get("conversation_context")
    if saved_context and conversation_history:
        conversation_history = f"{saved_context}\n\nRecent messages:\n{conversation_history}"
    elif saved_context:
        conversation_history = saved_context
    
    # Use LLM to classify intent with full conversation context
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0)
    
    router_prompt = get_prompt("router")
    
    # # Log the prompt being used
    # log_prompt("ROUTER", router_prompt, {
    #     "has_ordering_context": has_ordering_context if 'has_ordering_context' in locals() else False,
    #     "message_count": len(messages)
    # })
    
    # Use conversation history to understand context - let LLM decide based on full history
    # Don't force payment intent based on keywords - let the LLM analyze the full conversation
    conversation_history_lower = (conversation_history or "").lower()
    has_ordering_context = any(
        word in conversation_history_lower 
        for word in ["cart", "order", "add", "item", "quantity", "total", "checkout", "added to cart"]
    ) if conversation_history else False
    
    # Check if items were just added or cart was shown (contextual confirmation detection)
    # Look for recent cart operations in conversation history
    recent_messages_str = "\n".join([
        str(msg.content) for msg in messages[-5:] if hasattr(msg, 'content') and msg.content
    ]).lower()
    
    has_recent_cart_operation = any(
        phrase in recent_messages_str 
        for phrase in ["added to cart", "cart total", "cart summary", "items in cart", "view_cart"]
    )
    
    # Only force payment intent if there's STRONG evidence of ordering context AND confirmation
    # Don't force it for simple "yes" responses without ordering context
    current_message_lower = last_message.content.lower()
    completion_phrases = ["thats all", "that's all", "thats it", "that's it", "finalize", "finalise", "complete", "done", "ready", "let's finalize", "lets finalize", "finalize the order", "finalise the order", "complete the order", "ready to pay", "ready to checkout"]
    no_more_additions = "no" in current_message_lower and ("add" in current_message_lower or "change" in current_message_lower or "more" in current_message_lower) and (has_ordering_context or has_recent_cart_operation)
    
    # Only consider it confirmation if there's clear ordering context (cart operations happened)
    is_confirmation = (
        (any(phrase in current_message_lower for phrase in completion_phrases) or no_more_additions) 
        and (has_ordering_context or has_recent_cart_operation)
    )
    
    # Build classification prompt with conversation history (only if history exists)
    if conversation_history:
        classification_prompt = f"""{router_prompt}

CONVERSATION HISTORY:
{conversation_history}

CURRENT USER MESSAGE:
{last_message.content}

Based on the conversation history and current message, classify the intent.
{"NOTE: User said confirmation words - if in ordering context, this should be 'payment' intent." if is_confirmation and has_ordering_context else ""}"""
    else:
        # No conversation history (starting conversation)
        classification_prompt = f"""{router_prompt}

CURRENT USER MESSAGE:
{last_message.content}

Based on the current message, classify the intent."""
    
    # Log the full classification prompt
    log_prompt("ROUTER", classification_prompt, {
        "conversation_history_length": len(conversation_history) if conversation_history is not None else 0,
        "current_message": last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
        "has_history": conversation_history is not None
    })
    
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Intent Classification")
    response = llm.invoke([HumanMessage(content=classification_prompt)])
    response_time = time.time() - start_time
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Intent Classification", response_time)
    
    response_content = response.content.strip()
    response_lower = response_content.lower()
    
    # Check if response is a greeting (not an intent word)
    valid_intents = ["product_inquiry", "ordering", "payment", "cancellation", "general_qa"]
    is_greeting_response = response_lower not in [intent.lower() for intent in valid_intents] and len(response_content) > 10
    
    # If it's a greeting response, handle it directly
    if is_greeting_response:
        log_intent_classification("greeting", "greeting detected and handled by router")
        greeting_ai_message = AIMessage(content=response_content)
        
        log_agent_flow("ROUTER", "Greeting Handled Directly", {
            "user_message": last_message.content,
            "response": response_content[:50]
        })
        
        # Use Command to update state and end flow
        # add_messages reducer will APPEND greeting_ai_message to existing messages
        # All previous messages (human + AI) are preserved
        return create_message_update_command(
            [greeting_ai_message],
            state=state,
            goto="__end__",
            intent="greeting",
            conversation_context=None,
            active_agent=None
        )
    
    # Otherwise, it's an intent classification
    intent = response_lower
    
    # Only force payment intent if there's STRONG evidence (cart operations + explicit completion phrases)
    # Don't force for simple "yes" without clear ordering context
    if is_confirmation and (has_ordering_context or has_recent_cart_operation):
        intent = "payment"
        log_intent_classification(intent, "forced (confirmation in ordering context)")
    
    # Validate intent
    if intent not in valid_intents:
        log_intent_classification("general_qa", f"default (invalid: {intent})")
        intent = "general_qa"  # Default to general_qa if unclear
    else:
        if not (is_confirmation and has_ordering_context):  # Don't log if we already logged above
            log_intent_classification(intent, "valid")
    
    # Update conversation context for efficient memory (store summary of key points)
    # For now, we'll store a condensed version of recent history
    # In the future, this could be a summarized version generated by LLM
    if conversation_history:
        updated_context = conversation_history[-500:] if len(conversation_history) > 500 else conversation_history
    else:
        updated_context = None
    
    log_agent_flow("ROUTER", "Intent Classification Complete", {
        "intent": intent,
        "history_length": len(messages),
        "context_used": True
    })
    
    # Determine which agent should be active based on intent
    agent_mapping = {
        "product_inquiry": "qa_agent",
        "general_qa": "qa_agent",
        "ordering": "ordering_agent",
        "payment": "payment_agent",
        "cancellation": "cancellation_agent"
    }
    active_agent = agent_mapping.get(intent, "qa_agent")
    
    # Use Command to update state and route to appropriate agent
    # Router doesn't add new messages, just updates intent and context
    return Command(
        update={
            "intent": intent,
            "conversation_context": updated_context,
            "active_agent": active_agent
        },
        goto=active_agent
    )


def route_to_agent(state: ReceptionistState) -> Literal["qa_agent", "ordering_agent", "payment_agent", "cancellation_agent", "__end__"]:
    """Route to appropriate agent based on intent."""
    intent = state.get("intent", "general_qa")
    log_graph_flow("route_to_agent", "Routing Decision", {"intent": intent})
    
    # Greetings are handled directly in router, end the flow
    if intent == "greeting":
        log_agent_flow("ROUTER", "Greeting Handled - Ending Flow")
        return "__end__"
    elif intent == "product_inquiry" or intent == "general_qa":
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
