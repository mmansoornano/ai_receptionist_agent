"""Helper to add logging to LangChain tools."""
from functools import wraps
from utils.logger import log_tool_call


def log_tool_execution(tool_func):
    """Decorator to add logging to tool execution."""
    @wraps(tool_func)
    def wrapper(*args, **kwargs):
        tool_name = tool_func.name if hasattr(tool_func, 'name') else tool_func.__name__
        
        # Prepare params for logging
        params = {}
        if args:
            # Get parameter names from function signature
            import inspect
            sig = inspect.signature(tool_func)
            param_names = list(sig.parameters.keys())
            for i, arg in enumerate(args):
                if i < len(param_names):
                    params[param_names[i]] = str(arg)[:100]  # Truncate long values
        
        params.update({k: str(v)[:100] for k, v in kwargs.items()})
        
        # Log tool call
        log_tool_call(tool_name, params)
        
        # Execute tool
        try:
            result = tool_func(*args, **kwargs)
            # Log result (truncated)
            result_preview = str(result)[:200] if result else "None"
            log_tool_call(tool_name, params, result_preview)
            return result
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            log_tool_call(tool_name, params, error_msg)
            raise
    
    return wrapper
