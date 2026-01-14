"""Payment tools for payment agent."""
from langchain_core.tools import tool
from services.payment_service import (
    send_otp,
    verify_otp,
    confirm_payment,
    create_order,
    get_customer_service_phone
)
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


# Export tools list
PAYMENT_TOOLS = [
    send_payment_otp,
    verify_payment_otp,
    confirm_easypaisa_payment,
    create_order_from_cart
]
