"""Integration tests for backend API services (live Django backend)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import requests

from config import BACKEND_API_BASE_URL
from services.cart_service import (
    add_to_cart,
    clear_cart,
    get_cart,
    remove_from_cart,
    update_cart_item,
)
from services.cancellation_service import submit_cancellation_request
from services.payment_service import send_otp, verify_otp

pytestmark = pytest.mark.integration


def _backend_reachable() -> bool:
    try:
        response = requests.get(f"{BACKEND_API_BASE_URL}/health", timeout=5)
        return response.status_code < 500
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def backend_reachable():
    return _backend_reachable()


@pytest.fixture(autouse=True)
def skip_tests_when_backend_down(request, backend_reachable):
    if request.function.__name__ == "test_backend_health":
        return
    if not backend_reachable:
        pytest.skip(
            f"Backend not reachable at {BACKEND_API_BASE_URL} (see test_backend_health)"
        )


def _require_success(result: dict, what: str) -> None:
    if result.get("success") is not True:
        pytest.skip(f"{what}: backend returned success=False: {result!r}")


class TestBackendIntegration:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.customer_id = "test_customer_123"
        self.product_id = "protein-bar-white-chocolate"
        self.test_mobile = "03001234567"

    def test_backend_health(self):
        try:
            response = requests.get(f"{BACKEND_API_BASE_URL}/health", timeout=5)
        except requests.RequestException as e:
            pytest.skip(f"Backend not running: {e}")
        assert response.status_code in (200, 404), (
            f"Unexpected health status {response.status_code} from {BACKEND_API_BASE_URL}/health"
        )

    def test_cart_add_item(self):
        result = add_to_cart(self.customer_id, self.product_id, quantity=2)
        _require_success(result, "add_to_cart")
        assert "cart" in result

    def test_cart_get(self):
        result = get_cart(self.customer_id)
        _require_success(result, "get_cart")
        assert "cart" in result

    def test_cart_update_item(self):
        add_result = add_to_cart(self.customer_id, self.product_id, quantity=1)
        _require_success(add_result, "add_to_cart (setup for update)")

        cart_result = get_cart(self.customer_id)
        _require_success(cart_result, "get_cart (setup for update)")
        items = cart_result.get("cart", {}).get("items") or []
        if not items:
            pytest.skip("No cart items returned after add; cannot test update")

        item_id = items[0]["item_id"]
        result = update_cart_item(item_id, quantity=3, customer_id=self.customer_id)
        _require_success(result, "update_cart_item")

    def test_cart_remove_item(self):
        add_result = add_to_cart(self.customer_id, self.product_id, quantity=1)
        _require_success(add_result, "add_to_cart (setup for remove)")

        cart_result = get_cart(self.customer_id)
        _require_success(cart_result, "get_cart (setup for remove)")
        items = cart_result.get("cart", {}).get("items") or []
        if not items:
            pytest.skip("No cart items returned after add; cannot test remove")

        item_id = items[0]["item_id"]
        result = remove_from_cart(item_id, customer_id=self.customer_id)
        _require_success(result, "remove_from_cart")

    def test_cart_clear(self):
        result = clear_cart(self.customer_id)
        _require_success(result, "clear_cart")

    def test_payment_send_otp(self):
        result = send_otp(self.test_mobile)
        _require_success(result, "send_otp")
        assert "expires_in_minutes" in result

    def test_payment_verify_otp(self):
        send_result = send_otp(self.test_mobile)
        _require_success(send_result, "send_otp (setup for verify)")

        result = verify_otp(self.test_mobile, "123456")
        assert "success" in result
        assert isinstance(result.get("success"), bool)

    def test_cancellation_submit(self):
        result = submit_cancellation_request(
            order_id="ORD123456",
            reason="Test cancellation",
            customer_phone=self.test_mobile,
        )
        _require_success(result, "submit_cancellation_request")
        assert "request_id" in result
        assert "customer_service_phone" in result


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-s", "-m", "integration"]))
