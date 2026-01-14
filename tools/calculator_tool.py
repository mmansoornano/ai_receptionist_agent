"""Calculator tool for price calculations."""
from langchain_core.tools import tool
from utils.logger import log_tool_call


@tool
def calculate_price(*args: float) -> str:
    """Calculate the sum of multiple prices.
    
    Use this tool to add up product prices, calculate totals, or perform price calculations.
    
    Args:
        *args: One or more numeric values (prices) to add together
    
    Returns:
        String with the calculated total
    
    Examples:
        calculate_price(450.00, 220.00) -> "Total: PKR 670.00"
        calculate_price(450, 450, 200) -> "Total: PKR 1,100.00"
    """
    log_tool_call("calculate_price", {"args": args})
    
    try:
        # Convert all args to float and sum them
        total = sum(float(arg) for arg in args)
        
        # Format as PKR currency
        result = f"Total: PKR {total:,.2f}"
        log_tool_call("calculate_price", {"args": args}, result)
        return result
    except (ValueError, TypeError) as e:
        error_msg = f"Error calculating price: {str(e)}"
        log_tool_call("calculate_price", {"args": args}, error_msg)
        return error_msg


@tool
def multiply_price(price: float, quantity: int) -> str:
    """Multiply price by quantity.
    
    Use this tool to calculate the total price for multiple items of the same product.
    
    Args:
        price: The price per item
        quantity: The number of items
    
    Returns:
        String with the calculated total
    
    Examples:
        multiply_price(450.00, 3) -> "Total: PKR 1,350.00"
    """
    log_tool_call("multiply_price", {"price": price, "quantity": quantity})
    
    try:
        total = float(price) * int(quantity)
        result = f"Total: PKR {total:,.2f}"
        log_tool_call("multiply_price", {"price": price, "quantity": quantity}, result)
        return result
    except (ValueError, TypeError) as e:
        error_msg = f"Error calculating price: {str(e)}"
        log_tool_call("multiply_price", {"price": price, "quantity": quantity}, error_msg)
        return error_msg


# Export tools list
CALCULATOR_TOOLS = [calculate_price, multiply_price]
