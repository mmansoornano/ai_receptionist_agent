"""Product service for fetching catalog via backend API."""
from typing import Dict, List
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


def list_products() -> List[Dict]:
    """Fetch all active products from backend."""
    log_tool_call("product_list", {})
    try:
        result = _make_request("GET", "/api/products/")
        # DRF router returns list for ReadOnlyModelViewSet without pagination
        products = result if isinstance(result, list) else result.get("results", [])
        log_tool_call("product_list", {}, {"count": len(products), "products": products})
        return products
    except Exception as e:
        log_tool_call("product_list", {}, {"error": str(e)})
        return []
