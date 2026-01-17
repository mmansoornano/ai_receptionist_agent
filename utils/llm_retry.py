"""Retry utilities for LLM calls with exponential backoff."""
import time
import asyncio
from typing import Callable, Any, Optional, TypeVar, Coroutine
from functools import wraps
from langchain_core.messages import BaseMessage, AIMessage
from utils.logger import agent_logger, log_agent_flow

T = TypeVar('T')


def retry_llm_call(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    retryable_errors: tuple = (Exception,),
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)
):
    """Decorator for retrying LLM calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        backoff_factor: Multiplier for exponential backoff
        retryable_errors: Tuple of exception types to retry
        retryable_status_codes: Tuple of HTTP status codes to retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    is_retryable = isinstance(e, retryable_errors)
                    status_code = getattr(e, 'status_code', None)
                    
                    if status_code:
                        is_retryable = is_retryable or (status_code in retryable_status_codes)
                    
                    if not is_retryable:
                        agent_logger.error(f"❌ Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt < max_retries:
                        agent_logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay:.2f}s (error: {str(e)[:100]})")
                        log_agent_flow("RETRY", f"Retrying {func.__name__}", {
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay,
                            "error": str(e)[:100]
                        })
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        agent_logger.error(f"❌ Max retries exceeded for {func.__name__}: {e}")
                        raise
            
            # Should never reach here, but just in case
            raise last_exception or Exception(f"Failed after {max_retries} retries")
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    is_retryable = isinstance(e, retryable_errors)
                    status_code = getattr(e, 'status_code', None)
                    
                    if status_code:
                        is_retryable = is_retryable or (status_code in retryable_status_codes)
                    
                    if not is_retryable:
                        agent_logger.error(f"❌ Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt < max_retries:
                        agent_logger.warning(f"⚠️ Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay:.2f}s (error: {str(e)[:100]})")
                        log_agent_flow("RETRY", f"Retrying {func.__name__}", {
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay": delay,
                            "error": str(e)[:100]
                        })
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        agent_logger.error(f"❌ Max retries exceeded for {func.__name__}: {e}")
                        raise
            
            # Should never reach here, but just in case
            raise last_exception or Exception(f"Failed after {max_retries} retries")
        
        # Return appropriate wrapper based on whether function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invoke_with_retry(
    llm: Any,
    messages: list[BaseMessage],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    agent_name: str = "unknown"
) -> AIMessage:
    """Invoke LLM with retry logic for sync calls.
    
    Args:
        llm: LangChain LLM instance
        messages: List of messages to send
        max_retries: Maximum retry attempts
        initial_delay: Initial delay before retry
        agent_name: Name of agent (for logging)
    
    Returns:
        AIMessage response
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            response = llm.invoke(messages)
            if attempt > 0:
                agent_logger.info(f"✅ LLM call succeeded on retry {attempt + 1} for {agent_name}")
            return response
        except Exception as e:
            last_exception = e
            status_code = getattr(e, 'status_code', None)
            
            # Check if error is retryable (rate limits, server errors)
            is_retryable = status_code in (429, 500, 502, 503, 504) if status_code else True
            
            if not is_retryable or attempt >= max_retries:
                agent_logger.error(f"❌ LLM call failed for {agent_name} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if status_code:
                    log_agent_flow(agent_name.upper(), "LLM Error", {
                        "status_code": status_code,
                        "attempt": attempt + 1,
                        "error": str(e)[:100]
                    })
                raise
            
            agent_logger.warning(f"⚠️ Retrying LLM call for {agent_name} after {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
            time.sleep(delay)
            delay = min(delay * 2.0, 10.0)  # Exponential backoff, max 10s
    
    raise last_exception or Exception(f"LLM call failed after {max_retries} retries")


async def ainvoke_with_retry(
    llm: Any,
    messages: list[BaseMessage],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    agent_name: str = "unknown"
) -> AIMessage:
    """Invoke LLM with retry logic for async calls.
    
    Args:
        llm: LangChain LLM instance
        messages: List of messages to send
        max_retries: Maximum retry attempts
        initial_delay: Initial delay before retry
        agent_name: Name of agent (for logging)
    
    Returns:
        AIMessage response
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            response = await llm.ainvoke(messages)
            if attempt > 0:
                agent_logger.info(f"✅ LLM call succeeded on retry {attempt + 1} for {agent_name}")
            return response
        except Exception as e:
            last_exception = e
            status_code = getattr(e, 'status_code', None)
            
            # Check if error is retryable (rate limits, server errors)
            is_retryable = status_code in (429, 500, 502, 503, 504) if status_code else True
            
            if not is_retryable or attempt >= max_retries:
                agent_logger.error(f"❌ LLM call failed for {agent_name} (attempt {attempt + 1}/{max_retries + 1}): {e}")
                if status_code:
                    log_agent_flow(agent_name.upper(), "LLM Error", {
                        "status_code": status_code,
                        "attempt": attempt + 1,
                        "error": str(e)[:100]
                    })
                raise
            
            agent_logger.warning(f"⚠️ Retrying LLM call for {agent_name} after {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})")
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, 10.0)  # Exponential backoff, max 10s
    
    raise last_exception or Exception(f"LLM call failed after {max_retries} retries")
