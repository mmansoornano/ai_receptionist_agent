"""Cancellation service for order cancellation via backend API."""
from typing import Dict, Optional
import requests
from config import BACKEND_API_BASE_URL
from services.payment_service import get_customer_service_phone
from utils.logger import log_tool_call

# Dummy phone number for customer service
CUSTOMER_SERVICE_PHONE = get_customer_service_phone()


def _make_request(method: str, endpoint: str, **kwargs) -> Dict:
    """Make HTTP request to backend API."""
    url = f"{BACKEND_API_BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        log_tool_call("backend_api_error", {"endpoint": endpoint, "error": str(e)})
        raise


def submit_cancellation_request(order_id: str, reason: str, customer_phone: Optional[str] = None) -> Dict:
    """Submit cancellation request to admin (POST /api/cancellations/submit)."""
    log_tool_call("cancellation_submit", {"order_id": order_id, "reason": reason})
    
    try:
        payload = {
            "order_id": order_id,
            "reason": reason
        }
        if customer_phone:
            payload["customer_phone"] = customer_phone
        
        result = _make_request(
            "POST",
            "/api/cancellations/submit",
            json=payload
        )
        log_tool_call("cancellation_submit", {"order_id": order_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cancellation_submit", {"order_id": order_id}, error_result)
        return error_result


def get_customer_service_number() -> str:
    """Get customer service phone number for direct contact."""
    return CUSTOMER_SERVICE_PHONE
