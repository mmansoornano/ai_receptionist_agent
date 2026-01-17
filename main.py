"""Main entry point for the agent system."""
import time

from graph.main import receptionist_graph
from graph.state import ReceptionistState
from langchain_core.messages import HumanMessage
from config import DEFAULT_LANGUAGE, DEFAULT_CHANNEL, LLM_PROVIDER, OLLAMA_MODEL, OPENAI_MODEL
from utils.logger import (
    agent_logger, log_agent_flow, log_llm_call, log_error
)


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
        "phone": phone_number,
        "channel": channel,
        "language": language,
        "conversation_id": conversation_id,
        "customer_id": customer_id
    })
    agent_logger.info(f"📥 User Message: {message}")
    
    # Log LLM configuration
    model_name = OLLAMA_MODEL if LLM_PROVIDER == 'ollama' else OPENAI_MODEL
    log_llm_call(LLM_PROVIDER, model_name, "Configuration")
    
    try:
        # Check if this is a reset message
        message_lower = message.lower().strip()
        is_reset = any(keyword in message_lower for keyword in ["reset", "start over", "new conversation", "clear"])
        
        # If reset and customer_id exists, clear the cart
        if is_reset and customer_id:
            from services.cart_service import clear_cart
            try:
                clear_cart(customer_id)
                agent_logger.info(f"🛒 Cart cleared for customer_id: {customer_id}")
            except Exception as e:
                agent_logger.warning(f"⚠️ Failed to clear cart: {e}")
        
        # Create initial state
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
        
        # Run the graph
        agent_logger.info("🔄 Executing agent graph...")
        result = receptionist_graph.invoke(initial_state)
        
        # Log final intent
        final_intent = result.get("intent", "unknown")
        log_agent_flow("SYSTEM", "Graph Execution Complete", {
            "intent": final_intent,
            "execution_time": f"{time.time() - start_time:.2f}s"
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
                    agent_logger.info(f"📤 Agent Response: {response}")
                    agent_logger.info("=" * 80)
                    return response
        
        error_msg = "I didn't understand. Can you repeat?"
        agent_logger.warning(f"⚠️ No valid response generated, returning default message")
        agent_logger.info("=" * 80)
        return error_msg
        
    except Exception as e:
        log_error(e, "process_message")
        agent_logger.info("=" * 80)
        raise


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
