"""Cart management tools for ordering agent."""
from langchain_core.tools import tool
from services.cart_service import (
    add_to_cart,
    get_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart
)
from utils.logger import log_tool_call


@tool
def add_item_to_cart(product_id: str, quantity: int = 1, customer_id: str = "anonymous") -> str:
    """Add a product to the shopping cart.
    
    Args:
        product_id: The product ID to add (e.g., "protein-bar-white-chocolate")
        quantity: Quantity to add (default: 1)
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Success message with cart summary
    """
    log_tool_call("add_item_to_cart", {"product_id": product_id, "quantity": quantity, "customer_id": customer_id})
    
    result = add_to_cart(customer_id, product_id, quantity)
    
    if result.get("success"):
        cart = result.get("cart", {})
        message = f"Added {quantity} x {product_id} to cart. Cart total: Rs.{cart.get('total', 0):.2f}"
        log_tool_call("add_item_to_cart", {"product_id": product_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("add_item_to_cart", {"product_id": product_id}, error_msg)
        return error_msg


@tool
def view_cart(customer_id: str = "anonymous") -> str:
    """View the current shopping cart contents.
    
    Args:
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Formatted cart contents
    """
    log_tool_call("view_cart", {"customer_id": customer_id})
    
    result = get_cart(customer_id)
    
    if result.get("success"):
        cart = result.get("cart", {})
        items = cart.get("items", [])
        if not items:
            message = "Your cart is empty."
        else:
            items_text = "\n".join([
                f"- {item['name']} (Qty: {item['quantity']}) - Rs.{item['subtotal']:.2f}"
                for item in items
            ])
            message = f"Cart Contents:\n{items_text}\n\nTotal: Rs.{cart.get('total', 0):.2f}"
        
        log_tool_call("view_cart", {"customer_id": customer_id}, message[:200])
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("view_cart", {"customer_id": customer_id}, error_msg)
        return error_msg


@tool
def update_cart_quantity(item_id: str, quantity: int, customer_id: str = "anonymous") -> str:
    """Update the quantity of an item in the cart.
    
    Args:
        item_id: The item ID in the cart
        quantity: New quantity (set to 0 to remove)
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Success message
    """
    log_tool_call("update_cart_quantity", {"item_id": item_id, "quantity": quantity, "customer_id": customer_id})
    
    result = update_cart_item(item_id, quantity, customer_id)
    
    if result.get("success"):
        if quantity == 0:
            message = f"Removed item from cart."
        else:
            cart = result.get("cart", {})
            message = f"Updated quantity to {quantity}. Cart total: Rs.{cart.get('total', 0):.2f}"
        log_tool_call("update_cart_quantity", {"item_id": item_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("update_cart_quantity", {"item_id": item_id}, error_msg)
        return error_msg


@tool
def remove_item_from_cart(item_id: str, customer_id: str = "anonymous") -> str:
    """Remove an item from the cart.
    
    Args:
        item_id: The item ID in the cart
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Success message
    """
    log_tool_call("remove_item_from_cart", {"item_id": item_id, "customer_id": customer_id})
    
    result = remove_from_cart(item_id, customer_id)
    
    if result.get("success"):
        cart = result.get("cart", {})
        message = f"Removed item from cart. Cart total: Rs.{cart.get('total', 0):.2f}"
        log_tool_call("remove_item_from_cart", {"item_id": item_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("remove_item_from_cart", {"item_id": item_id}, error_msg)
        return error_msg


@tool
def clear_shopping_cart(customer_id: str = "anonymous") -> str:
    """Clear all items from the shopping cart.
    
    Args:
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Success message
    """
    log_tool_call("clear_shopping_cart", {"customer_id": customer_id})
    
    result = clear_cart(customer_id)
    
    if result.get("success"):
        message = "Cart cleared successfully."
        log_tool_call("clear_shopping_cart", {"customer_id": customer_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("clear_shopping_cart", {"customer_id": customer_id}, error_msg)
        return error_msg


# Export tools list
CART_TOOLS = [
    add_item_to_cart,
    view_cart,
    update_cart_quantity,
    remove_item_from_cart,
    clear_shopping_cart
]
