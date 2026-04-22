"""Cancellation tools for cancellation agent."""
from langchain_core.tools import tool
from services.cancellation_service import (
    submit_cancellation_request,
    get_customer_service_number
)
from utils.logger import log_tool_call


@tool
def submit_order_cancellation(order_id: str, reason: str, customer_phone: str = None) -> str:
    """Submit a staff follow-up request about an order (e.g. rare pre-baking case). Does not guarantee refund.

    Store policy: once baking has started, orders are not cancelled or refunded via this chat.

    Args:
        order_id: Order ID
        reason: Short reason
        customer_phone: Optional customer phone

    Returns:
        Confirmation that the request was logged, plus how to reach customer service.
    """
    log_tool_call("submit_order_cancellation", {"order_id": order_id, "reason": reason})
    
    result = submit_cancellation_request(order_id, reason, customer_phone)
    
    if result["success"]:
        phone = get_customer_service_number()
        message = (
            f"Request recorded for staff (Request ID: {result['request_id']}). "
            f"We do not offer refunds or cancellations after baking has started. "
            f"For order questions, call customer service at {phone}."
        )
        log_tool_call("submit_order_cancellation", {"order_id": order_id}, message)
        return message
    else:
        error_msg = f"Error: {result.get('error', 'Unknown error')}"
        log_tool_call("submit_order_cancellation", {"order_id": order_id}, error_msg)
        return error_msg


@tool
def get_cancellation_contact_info() -> str:
    """Customer service phone for order questions. Policy: no refund or cancel after baking starts.
    
    Returns:
        Contact line with phone number
    """
    log_tool_call("get_cancellation_contact_info", {})
    
    phone = get_customer_service_number()
    message = (
        f"Customer service (order questions, timing before production): {phone}. "
        f"Note: once baking has started for an order, we do not offer cancellation or refund."
    )
    
    log_tool_call("get_cancellation_contact_info", {}, message)
    return message


# Export tools list
CANCELLATION_TOOLS = [
    submit_order_cancellation,
    get_cancellation_contact_info
]
