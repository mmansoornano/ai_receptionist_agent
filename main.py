"""Main entry point for the agent system."""
import os
import re
import time

from graph.main import receptionist_graph
from graph.state import ReceptionistState
from langchain_core.messages import HumanMessage
from config import DEFAULT_LANGUAGE, DEFAULT_CHANNEL, LLM_PROVIDER, OLLAMA_MODEL, OPENAI_MODEL
from utils.logger import (
    agent_logger, log_agent_flow, log_llm_call, log_error
)


def _pii_full_logging() -> bool:
    """Set AGENT_LOG_PII=1 to log full phone/customer ids and full user text at INFO."""
    return os.environ.get("AGENT_LOG_PII", "").lower() in ("1", "true", "yes")


def _mask_identifier(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    if _pii_full_logging():
        return value
    v = str(value).strip()
    if len(v) <= 4:
        return f"{label}:***"
    return f"{label}:{v[:2]}…{v[-2:]}(n={len(v)})"


def _preview_user_message(text: str) -> str:
    if _pii_full_logging():
        return text
    if len(text) <= 240:
        return text
    return text[:240] + "…"


def process_message(
    message: str,
    phone_number: str,
    channel: str = DEFAULT_CHANNEL,
    language: str = DEFAULT_LANGUAGE,
    conversation_id: str = None,
    customer_id: str = None
) -> str:
    """Process a user message through the agent system.
    
    Args:
        message: User message text
        phone_number: User phone number
        channel: Communication channel ('voice' or 'sms')
        language: Language code (default: 'en' for English)
        conversation_id: Optional conversation ID
        customer_id: Optional customer ID
    
    Returns:
        Agent response text
    """
    start_time = time.time()
    
    # Log incoming message
    agent_logger.info("=" * 80)
    log_agent_flow("SYSTEM", "Processing Message", {
        "phone": _mask_identifier(phone_number, label="phone"),
        "channel": channel,
        "language": language,
        "conversation_id": _mask_identifier(conversation_id, label="conv"),
        "customer_id": _mask_identifier(customer_id, label="cust"),
    })
    agent_logger.info(f"📥 User Message: {_preview_user_message(message)}")
    
    # Log LLM configuration
    model_name = OLLAMA_MODEL if LLM_PROVIDER == 'ollama' else OPENAI_MODEL
    log_llm_call(LLM_PROVIDER, model_name, "Configuration")
    
    try:
        # Use conversation_id or customer_id as thread_id for state persistence
        from utils.state_utils import get_thread_id, get_config, reset_conversation_state
        thread_id = get_thread_id(conversation_id, customer_id, phone_number)
        config = get_config(thread_id)
        
        # Check if this is a reset message
        message_lower = message.lower().strip()
        is_reset = any(keyword in message_lower for keyword in ["reset", "start over", "new conversation", "clear"])
        
        # Handle reset: clear state and cart
        if is_reset:
            # Clear conversation state (checkpointer)
            reset_conversation_state(conversation_id, customer_id, phone_number)
            
            # Clear cart if customer_id exists
            if customer_id:
                from services.cart_service import clear_cart
                try:
                    clear_cart(customer_id)
                    agent_logger.info(f"🛒 Cart cleared for customer_id: {customer_id}")
                except Exception as e:
                    agent_logger.warning(f"⚠️ Failed to clear cart: {e}")
            
            # Return reset confirmation message
            return "Conversation has been reset. How can I help you today?"
        
        # Get existing state from checkpointer (if any)
        try:
            current_state = receptionist_graph.get_state(config)
            existing_messages = current_state.values.get("messages", []) if current_state.values else []
            existing_customer_id = current_state.values.get("customer_id") if current_state.values else None
            
            # Use existing customer_id if not provided (for state continuity)
            if not customer_id and existing_customer_id:
                customer_id = existing_customer_id
                agent_logger.info(
                    f"🔄 Using existing customer_id from state: {_mask_identifier(customer_id, label='cust')}"
                )
            
            agent_logger.info(
                f"📊 Existing state: {len(existing_messages)} messages, customer_id: "
                f"{_mask_identifier(existing_customer_id, label='cust')}"
            )
        except Exception as e:
            # First message in conversation - no existing state
            existing_messages = []
            agent_logger.info(f"🆕 Starting new conversation: {thread_id}")
        
        # Create state with only new message - reducer will merge with existing from checkpointer
        initial_state: ReceptionistState = {
            "messages": [HumanMessage(content=message)],
            "intent": None,
            "conversation_context": None,
            "customer_info": None,
            "appointment_data": None,
            "channel": channel,
            "language": language,
            "conversation_id": conversation_id,
            "customer_id": customer_id,
        }
        
        # Run the graph with config for state persistence
        agent_logger.info("🔄 Executing agent graph...")
        workflow_start_time = time.time()
        
        try:
            # Note: Proper timeout handling would require async (astream with asyncio.timeout)
            # For sync invoke, we rely on LLM service timeouts and log execution time
            result = receptionist_graph.invoke(initial_state, config)
            workflow_time = time.time() - workflow_start_time
            
            # Warn if execution took too long (but don't fail)
            if workflow_time > 60:
                agent_logger.warning(f"⏱️ Graph execution took {workflow_time:.2f}s (slow)")
        except Exception as e:
            workflow_time = time.time() - workflow_start_time
            agent_logger.error(f"❌ Graph execution error after {workflow_time:.2f}s: {e}")
            log_error(e, "graph_invoke")
            # Return user-friendly error message instead of raising
            return "Oh, something went wrong there. Can you try typing that in a different way?"
        
        # Get final state from checkpointer for comprehensive logging
        try:
            final_state = receptionist_graph.get_state(config)
            final_message_count = len(final_state.values.get("messages", [])) if final_state.values else 0
            
            log_agent_flow("SYSTEM", "State After Execution", {
                "final_message_count": final_message_count,
                "thread_id": thread_id
            })
        except Exception as e:
            agent_logger.warning(f"⚠️ Could not retrieve final state: {e}")
        
        # Log final intent and execution time
        final_intent = result.get("intent", "unknown")
        total_time = time.time() - start_time
        log_agent_flow("SYSTEM", "Graph Execution Complete", {
            "intent": final_intent,
            "execution_time": f"{total_time:.2f}s",
            "workflow_time": f"{workflow_time:.2f}s" if 'workflow_time' in locals() else "N/A"
        })
        
        # Get the last AI message with content (skip ToolMessages and tool call JSON)
        from langchain_core.messages import AIMessage, ToolMessage
        messages = result.get("messages", [])
        if messages:
            # Filter out ToolMessages completely - they should never be displayed
            ai_messages = [msg for msg in messages if isinstance(msg, AIMessage) and not isinstance(msg, ToolMessage)]
            
            # Find the last AIMessage with content (not just tool calls)
            for msg in reversed(ai_messages):
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    response = msg.content.strip()
                    # Additional check: if response looks like JSON tool output, skip it
                    if response.startswith('{') and ('"name":' in response or '"parameters":' in response):
                        agent_logger.warning(f"⚠️ Skipping tool call JSON in response: {response[:100]}...")
                        continue
                    # Strip "Customer ID: X - use this for all cart tools." (internal, never show in chat)
                    lines = response.split("\n")
                    filtered = [L for L in lines if not re.match(r"^\s*Customer ID:\s*\d+\s*-\s*use this for all cart tools\.?\s*$", L)]
                    response = "\n".join(filtered).strip()
                    agent_logger.info(f"📤 Agent Response: {_preview_user_message(response)}")
                    agent_logger.info("=" * 80)
                    return response
        
        error_msg = "I didn't understand. Can you repeat?"
        agent_logger.warning(f"⚠️ No valid response generated, returning default message")
        agent_logger.info("=" * 80)
        return error_msg
        
    except Exception as e:
        log_error(e, "process_message")
        agent_logger.error(f"❌ Fatal error in process_message: {e}")
        agent_logger.info("=" * 80)
        # Return user-friendly error message instead of raising
        return "I'm sorry, something unexpected happened. Please try again in a moment."


if __name__ == "__main__":
    # Interactive mode for testing
    print("AI Receptionist - Interactive Mode")
    print("Type 'quit' or 'exit' to end the conversation\n")
    
    phone_number = "+1234567890"
    conversation_id = None
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            response = process_message(
                user_input,
                phone_number=phone_number,
                channel="sms",
                conversation_id=conversation_id
            )
            
            print(f"\nAI: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
