"""Payment tools for payment agent."""
from langchain_core.tools import tool
from services.payment_service import (
    send_otp,
    verify_otp,
    confirm_payment,
    create_order,
    get_customer_service_phone
)
from services.cart_service import get_cart
from utils.logger import log_tool_call


@tool
def send_payment_otp(mobile_number: str) -> str:
    """Send OTP to mobile number for payment verification.
    
    Args:
        mobile_number: Mobile number (e.g., "03001234567")
    
    Returns:
        Success message with OTP information (for demo, includes OTP)
    """
    log_tool_call("send_payment_otp", {"mobile_number": mobile_number})
    
    result = send_otp(mobile_number)
    
    if result["success"]:
        # In demo mode, include OTP in message (real implementation wouldn't)
        message = f"OTP has been sent to {mobile_number}. OTP: {result['otp']} (expires in {result['expires_in_minutes']} minutes)"
        log_tool_call("send_payment_otp", {"mobile_number": mobile_number}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("send_payment_otp", {"mobile_number": mobile_number}, error_msg)
        return error_msg


@tool
def verify_payment_otp(mobile_number: str, otp: str) -> str:
    """Verify OTP for payment.
    
    Args:
        mobile_number: Mobile number
        otp: OTP code received
    
    Returns:
        Verification result message
    """
    log_tool_call("verify_payment_otp", {"mobile_number": mobile_number, "otp": otp})
    
    result = verify_otp(mobile_number, otp)
    
    if result["success"]:
        message = "OTP verified successfully. You can now proceed with payment."
        log_tool_call("verify_payment_otp", {"mobile_number": mobile_number}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("verify_payment_otp", {"mobile_number": mobile_number}, error_msg)
        return error_msg


@tool
def confirm_easypaisa_payment(mobile_number: str, amount: float) -> str:
    """Confirm payment via Easypaisa.
    
    Args:
        mobile_number: Mobile number
        amount: Payment amount
    
    Returns:
        Payment confirmation message
    """
    log_tool_call("confirm_easypaisa_payment", {"mobile_number": mobile_number, "amount": amount})
    
    result = confirm_payment(mobile_number, amount)
    
    if result["success"]:
        message = f"Payment confirmed successfully! Transaction ID: {result['transaction_id']}, Amount: Rs.{result['amount']:.2f}"
        log_tool_call("confirm_easypaisa_payment", {"mobile_number": mobile_number}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("confirm_easypaisa_payment", {"mobile_number": mobile_number}, error_msg)
        return error_msg


@tool
def view_cart(customer_id: str = "anonymous") -> str:
    """View the current shopping cart contents to get cart data for payment.
    
    Use this tool FIRST when user wants to proceed to payment - it fetches current cart items and total.
    
    Args:
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Cart summary with items, quantities, prices, and total
    """
    log_tool_call("view_cart", {"customer_id": customer_id})
    
    result = get_cart(customer_id)
    
    if result.get("success") and result.get("cart"):
        cart = result["cart"]
        items = cart.get("items", [])
        total = cart.get("total", 0)
        
        if items:
            message = f"Cart contains {len(items)} item(s):\n"
            for item in items:
                message += f"- {item.get('name', 'Unknown')} (x{item.get('quantity', 1)}) - Rs.{item.get('subtotal', 0):.2f}\n"
            message += f"\nSubtotal: Rs.{total:.2f}\nTotal with delivery (Rs.150): Rs.{total + 150:.2f}"
        else:
            message = "Cart is empty."
        log_tool_call("view_cart", {"customer_id": customer_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Failed to fetch cart')}"
        log_tool_call("view_cart", {"customer_id": customer_id}, error_msg)
        return error_msg


@tool
def create_order_from_cart(cart_data: dict, transaction_id: str) -> str:
    """Create order after payment confirmation.
    
    Args:
        cart_data: Cart data dictionary with items and total
        transaction_id: Payment transaction ID
    
    Returns:
        Order confirmation message
    """
    log_tool_call("create_order_from_cart", {"transaction_id": transaction_id})
    
    result = create_order(cart_data, transaction_id)
    
    if result["success"]:
        order = result["order"]
        message = f"Order created successfully! Order ID: {order['order_id']}, Total: Rs.{order['total']:.2f}"
        log_tool_call("create_order_from_cart", {"transaction_id": transaction_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("create_order_from_cart", {"transaction_id": transaction_id}, error_msg)
        return error_msg


@tool
def process_payment(customer_id: str = "anonymous") -> str:
    """Process payment and confirm order. This tool simulates payment processing and automatically confirms the payment after 2 seconds.
    
    Call this tool AFTER providing the payment link to the user. It will:
    1. Wait 2 seconds to simulate payment processing
    2. Automatically confirm the payment
    3. Create the order
    4. Return confirmation that payment was received and order has been placed
    
    Args:
        customer_id: Customer ID (default: "anonymous")
    
    Returns:
        Confirmation message that payment was received and order has been placed
    """
    import time
    log_tool_call("process_payment", {"customer_id": customer_id})
    
    # Simulate payment processing delay (2 seconds)
    time.sleep(2)
    
    # Get cart to create order
    cart_result = get_cart(customer_id)
    
    if cart_result.get("success") and cart_result.get("cart"):
        cart = cart_result["cart"]
        items = cart.get("items", [])
        total = cart.get("total", 0)
        
        # Generate a dummy transaction ID
        import uuid
        transaction_id = str(uuid.uuid4())[:8]
        
        # Create order from cart
        cart_data = {
            "items": items,
            "total": total,
            "customer_id": customer_id
        }
        
        order_result = create_order(cart_data, transaction_id)
        
        if order_result.get("success"):
            order = order_result.get("order", {})
            message = f"✅ Payment received successfully! Your order has been placed.\n\nOrder ID: {order.get('order_id', transaction_id)}\nTotal Amount: Rs.{total + 150:.2f} (including Rs.150 delivery charge)\n\nThank you for your purchase!"
            log_tool_call("process_payment", {"customer_id": customer_id, "transaction_id": transaction_id}, message)
            return message
        else:
            error_msg = f"Payment processed but order creation failed: {order_result.get('error', 'Unknown error')}"
            log_tool_call("process_payment", {"customer_id": customer_id}, error_msg)
            return error_msg
    else:
        error_msg = f"Payment processing failed: Could not fetch cart data. {cart_result.get('error', 'Cart is empty or not found')}"
        log_tool_call("process_payment", {"customer_id": customer_id}, error_msg)
        return error_msg


# Export tools list
PAYMENT_TOOLS = [
    view_cart,
    send_payment_otp,
    verify_payment_otp,
    confirm_easypaisa_payment,
    create_order_from_cart,
    process_payment
]
