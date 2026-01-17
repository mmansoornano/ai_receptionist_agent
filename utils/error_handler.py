"""Enhanced error handling utilities with specific HTTP status code handling."""
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage
from langgraph.types import Command
from graph.state import ReceptionistState
from utils.logger import agent_logger, log_agent_flow


def handle_llm_error(
    error: Exception,
    agent_name: str,
    state: ReceptionistState,
    default_message: str = "I'm sorry, there was an error processing your request. Please try again later."
) -> Command:
    """Handle LLM errors with specific responses based on error type.
    
    Args:
        error: Exception that occurred
        agent_name: Name of agent where error occurred
        state: Current state
        default_message: Default error message
    
    Returns:
        Command with error response
    """
    status_code = getattr(error, 'status_code', None)
    error_message = str(error)
    
    # Handle specific HTTP status codes
    if status_code == 429:
        # Rate limit exceeded
        response_message = "I'm really sorry, I've got more people talking to me than I can handle. Can you try again in 5 minutes or so?"
        log_agent_flow(agent_name.upper(), "Rate Limit Error", {
            "status_code": status_code,
            "error": error_message[:100]
        })
    elif status_code == 529:
        # Service overloaded (Cloudflare)
        response_message = "I'm really sorry, I've got more people talking to me than I can handle. Can you try again in 5 minutes or so?"
        log_agent_flow(agent_name.upper(), "Service Overload Error", {
            "status_code": status_code,
            "error": error_message[:100]
        })
    elif status_code in (500, 502, 503, 504):
        # Server errors
        response_message = "I'm sorry, there was an error on our end. Please try again in a moment."
        log_agent_flow(agent_name.upper(), "Server Error", {
            "status_code": status_code,
            "error": error_message[:100]
        })
    elif status_code == 401:
        # Authentication error
        response_message = default_message
        agent_logger.error(f"❌ Authentication error in {agent_name}: {error_message}")
        log_agent_flow(agent_name.upper(), "Authentication Error", {
            "status_code": status_code
        })
    elif status_code == 400:
        # Bad request
        response_message = "Oh, something went wrong there. Can you try typing that in a different way?"
        log_agent_flow(agent_name.upper(), "Bad Request Error", {
            "status_code": status_code,
            "error": error_message[:100]
        })
    else:
        # Generic error
        response_message = default_message
        log_agent_flow(agent_name.upper(), "Generic Error", {
            "status_code": status_code,
            "error": error_message[:100] if error_message else "Unknown error"
        })
    
    agent_logger.error(f"❌ Error in {agent_name}: {error_message}")
    
    # Return Command with error response
    from utils.message_utils import create_message_update_command
    
    return create_message_update_command(
        [AIMessage(content=response_message)],
        state=state,
        goto="__end__",
        active_agent=agent_name
    )


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable.
    
    Args:
        error: Exception to check
    
    Returns:
        True if error is retryable, False otherwise
    """
    status_code = getattr(error, 'status_code', None)
    
    if status_code:
        # Retry on rate limits, server errors, timeouts
        retryable_codes = (429, 500, 502, 503, 504, 529)
        return status_code in retryable_codes
    
    # Retry on network errors, timeouts (if detectable)
    error_type = type(error).__name__
    retryable_types = ("TimeoutError", "ConnectionError", "NetworkError")
    
    return any(retry_type in error_type for retry_type in retryable_types)


def get_user_friendly_error_message(error: Exception) -> str:
    """Get user-friendly error message from exception.
    
    Args:
        error: Exception that occurred
    
    Returns:
        User-friendly error message
    """
    status_code = getattr(error, 'status_code', None)
    
    if status_code == 429 or status_code == 529:
        return "I'm really sorry, I've got more people talking to me than I can handle. Can you try again in 5 minutes or so?"
    elif status_code in (500, 502, 503, 504):
        return "I'm sorry, there was an error on our end. Please try again in a moment."
    elif status_code == 400:
        return "Oh, something went wrong there. Can you try typing that in a different way?"
    else:
        return "I'm sorry, there was an error processing your request. Please try again later."
