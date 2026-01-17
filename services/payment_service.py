"""Payment service for Easypaisa payment via backend API."""
from typing import Dict, Optional
import requests
from config import BACKEND_API_BASE_URL
from utils.logger import log_tool_call

# Dummy phone number for customer service (should come from backend config)
CUSTOMER_SERVICE_PHONE = "+92-300-1234567"


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


def send_otp(mobile_number: str) -> Dict:
    """Send OTP to mobile number (POST /api/payment/otp/send/)."""
    log_tool_call("payment_send_otp", {"mobile_number": mobile_number})
    
    try:
        result = _make_request(
            "POST",
            "/api/payment/otp/send/",
            json={"mobile_number": mobile_number}
        )
        log_tool_call("payment_send_otp", {"mobile_number": mobile_number}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("payment_send_otp", {"mobile_number": mobile_number}, error_result)
        return error_result


def verify_otp(mobile_number: str, otp: str) -> Dict:
    """Verify OTP (POST /api/payment/otp/verify/)."""
    log_tool_call("payment_verify_otp", {"mobile_number": mobile_number, "otp": otp})
    
    try:
        result = _make_request(
            "POST",
            "/api/payment/otp/verify/",
            json={
                "mobile_number": mobile_number,
                "otp": otp
            }
        )
        log_tool_call("payment_verify_otp", {"mobile_number": mobile_number}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("payment_verify_otp", {"mobile_number": mobile_number}, error_result)
        return error_result


def confirm_payment(mobile_number: str, amount: float, order_id: Optional[str] = None) -> Dict:
    """Confirm payment via Easypaisa (POST /api/payment/easypaisa/confirm/)."""
    log_tool_call("payment_confirm", {"mobile_number": mobile_number, "amount": amount, "order_id": order_id})
    
    try:
        payload = {
            "mobile_number": mobile_number,
            "amount": amount
        }
        if order_id:
            payload["order_id"] = order_id
        
        result = _make_request(
            "POST",
            "/api/payment/easypaisa/confirm/",
            json=payload
        )
        log_tool_call("payment_confirm", {"mobile_number": mobile_number, "amount": amount}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("payment_confirm", {"mobile_number": mobile_number, "amount": amount}, error_result)
        return error_result


def create_order(cart_data: Dict, transaction_id: str) -> Dict:
    """Create order after payment (POST /api/orders/create/)."""
    log_tool_call("order_create", {"transaction_id": transaction_id})
    
    try:
        result = _make_request(
            "POST",
            "/api/orders/create/",
            json={
                "cart_data": cart_data,
                "transaction_id": transaction_id
            }
        )
        log_tool_call("order_create", {"transaction_id": transaction_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("order_create", {"transaction_id": transaction_id}, error_result)
        return error_result


def create_simple_payment(mobile_number: str, amount: float, transaction_id: Optional[str] = None, customer_id: Optional[str] = None) -> Dict:
    """Create payment directly with status=confirmed (POST /api/payment/create-simple/)."""
    log_tool_call("payment_create_simple", {"mobile_number": mobile_number, "amount": amount, "transaction_id": transaction_id})
    
    try:
        payload = {
            "mobile_number": mobile_number,
            "amount": amount
        }
        if transaction_id:
            payload["transaction_id"] = transaction_id
        if customer_id:
            payload["customer_id"] = customer_id
        
        result = _make_request(
            "POST",
            "/api/payment/create-simple/",
            json=payload
        )
        log_tool_call("payment_create_simple", {"mobile_number": mobile_number, "amount": amount}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("payment_create_simple", {"mobile_number": mobile_number, "amount": amount}, error_result)
        return error_result


def get_customer_service_phone() -> str:
    """Get customer service phone number for cancellations."""
    return CUSTOMER_SERVICE_PHONE
