"""Customer service for managing customer data via backend API."""
from typing import Dict, Optional
import requests
from config import BACKEND_API_BASE_URL
from utils.logger import log_tool_call


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


def get_customer(customer_id: str) -> Dict:
    """Get customer information by customer_id (GET /api/customers/{id}/)."""
    log_tool_call("customer_get", {"customer_id": customer_id})
    
    try:
        # Try to get customer by user_id first (customer_id is usually user.id)
        # If that fails, try as direct customer ID
        result = _make_request(
            "GET",
            f"/api/customers/{customer_id}/"
        )
        log_tool_call("customer_get", {"customer_id": customer_id}, result)
        return result
    except Exception as e:
        error_result = {"error": str(e)}
        log_tool_call("customer_get", {"customer_id": customer_id}, error_result)
        return error_result


def update_delivery_address(customer_id: Optional[str], delivery_address: str, phone: Optional[str] = None) -> Dict:
    """Update delivery address (POST /api/customers/address)."""
    payload = {
        "delivery_address": delivery_address,
    }
    if customer_id:
        payload["customer_id"] = customer_id
    if phone:
        payload["phone"] = phone

    log_tool_call("customer_update_address", payload)

    try:
        result = _make_request(
            "POST",
            "/api/customers/address/",
            json=payload
        )
        log_tool_call("customer_update_address", payload, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("customer_update_address", payload, error_result)
        return error_result
