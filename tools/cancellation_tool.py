"""Cancellation tools for cancellation agent."""
from langchain_core.tools import tool
from services.cancellation_service import (
    submit_cancellation_request,
    get_customer_service_number
)
from utils.logger import log_tool_call


@tool
def submit_order_cancellation(order_id: str, reason: str, customer_phone: str = None) -> str:
    """Submit order cancellation request to admin.
    
    Args:
        order_id: Order ID to cancel
        reason: Cancellation reason
        customer_phone: Optional customer phone number
    
    Returns:
        Cancellation request confirmation message
    """
    log_tool_call("submit_order_cancellation", {"order_id": order_id, "reason": reason})
    
    result = submit_cancellation_request(order_id, reason, customer_phone)
    
    if result["success"]:
        phone = get_customer_service_number()
        message = f"Cancellation request submitted successfully (Request ID: {result['request_id']}). For refund and reimbursement, please contact customer service at {phone}."
        log_tool_call("submit_order_cancellation", {"order_id": order_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("submit_order_cancellation", {"order_id": order_id}, error_msg)
        return error_msg


@tool
def get_cancellation_contact_info() -> str:
    """Get customer service contact information for cancellations and refunds.
    
    Returns:
        Customer service phone number
    """
    log_tool_call("get_cancellation_contact_info", {})
    
    phone = get_customer_service_number()
    message = f"For order cancellations, refunds, and reimbursements, please contact customer service at {phone}."
    
    log_tool_call("get_cancellation_contact_info", {}, message)
    return message


# Export tools list
CANCELLATION_TOOLS = [
    submit_order_cancellation,
    get_cancellation_contact_info
]
