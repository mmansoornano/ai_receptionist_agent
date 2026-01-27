"""Cart service for managing shopping cart via backend API."""
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
    except requests.exceptions.HTTPError as e:
        body = None
        try:
            if e.response is not None and e.response.content:
                body = e.response.json()
        except Exception:
            body = (e.response.text[:500] if e.response and e.response.text else None)
        err = str(e)
        if body is not None:
            err = f"{e.response.status_code} {err}; body={body}"
        log_tool_call("backend_api_error", {"endpoint": endpoint, "error": err})
        raise ValueError(err) from e
    except requests.exceptions.RequestException as e:
        log_tool_call("backend_api_error", {"endpoint": endpoint, "error": str(e)})
        raise


def add_to_cart(customer_id: str, product_id: str, quantity: int = 1) -> Dict:
    """Add item to cart (POST /api/cart/add/)."""
    log_tool_call("cart_add_item", {"customer_id": customer_id, "product_id": product_id, "quantity": quantity})

    try:
        result = _make_request(
            "POST",
            "/api/cart/add/",
            json={
                "product_id": product_id,
                "quantity": quantity,
                "customer_id": customer_id
            }
        )
        log_tool_call("cart_add_item", {"customer_id": customer_id, "product_id": product_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_add_item", {"customer_id": customer_id, "product_id": product_id}, error_result)
        return error_result


def add_to_cart_batch(customer_id: str, items: list) -> Dict:
    """Add multiple items to cart (POST /api/cart/add-batch/).
    items: list of {"product_id": str, "quantity": int}
    """
    log_tool_call("cart_add_batch", {"customer_id": customer_id, "item_count": len(items)})
    try:
        result = _make_request(
            "POST",
            "/api/cart/add-batch/",
            json={"customer_id": customer_id, "items": items}
        )
        log_tool_call("cart_add_batch", {"customer_id": customer_id, "item_count": len(items)}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_add_batch", {"customer_id": customer_id, "items": items}, error_result)
        return error_result


def get_cart(customer_id: str = "anonymous") -> Dict:
    """Get cart contents (GET /api/cart/)."""
    log_tool_call("cart_get", {"customer_id": customer_id})
    
    try:
        result = _make_request(
            "GET",
            "/api/cart/",
            params={"customer_id": customer_id}
        )
        log_tool_call("cart_get", {"customer_id": customer_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_get", {"customer_id": customer_id}, error_result)
        return error_result


def update_cart_item(item_id: str, quantity: int, customer_id: str = "anonymous") -> Dict:
    """Update cart item quantity (PUT /api/cart/item/:id/)."""
    log_tool_call("cart_update_item", {"item_id": item_id, "quantity": quantity, "customer_id": customer_id})
    
    try:
        result = _make_request(
            "PUT",
            f"/api/cart/item/{item_id}/",
            json={
                "quantity": quantity,
                "customer_id": customer_id
            }
        )
        log_tool_call("cart_update_item", {"item_id": item_id, "customer_id": customer_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_update_item", {"item_id": item_id, "customer_id": customer_id}, error_result)
        return error_result


def remove_from_cart(item_id: str, customer_id: str = "anonymous") -> Dict:
    """Remove item from cart (DELETE /api/cart/item/:id/)."""
    log_tool_call("cart_remove_item", {"item_id": item_id, "customer_id": customer_id})
    
    try:
        result = _make_request(
            "DELETE",
            f"/api/cart/item/{item_id}/",
            params={"customer_id": customer_id}
        )
        log_tool_call("cart_remove_item", {"item_id": item_id, "customer_id": customer_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_remove_item", {"item_id": item_id, "customer_id": customer_id}, error_result)
        return error_result


def clear_cart(customer_id: str = "anonymous") -> Dict:
    """Clear entire cart (DELETE /api/cart/)."""
    log_tool_call("cart_clear", {"customer_id": customer_id})
    
    try:
        result = _make_request(
            "DELETE",
            "/api/cart/",
            params={"customer_id": customer_id}
        )
        log_tool_call("cart_clear", {"customer_id": customer_id}, result)
        return result
    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        log_tool_call("cart_clear", {"customer_id": customer_id}, error_result)
        return error_result
