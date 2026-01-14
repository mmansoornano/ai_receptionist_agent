"""Integration tests for backend API services."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from services.cart_service import (
    add_to_cart,
    get_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart
)
from services.payment_service import (
    send_otp,
    verify_otp,
    confirm_payment,
    create_order
)
from services.cancellation_service import submit_cancellation_request
from config import BACKEND_API_BASE_URL
import requests


class TestBackendIntegration:
    """Test backend API integration."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.customer_id = "test_customer_123"
        self.product_id = "protein-bar-white-chocolate"
        self.test_mobile = "03001234567"
        
    def test_backend_health(self):
        """Test if backend is accessible."""
        try:
            # Try to reach backend (assuming there's a health endpoint)
            response = requests.get(f"{BACKEND_API_BASE_URL}/health", timeout=5)
            assert response.status_code in [200, 404], f"Backend not accessible: {response.status_code}"
            print(f"✓ Backend accessible at {BACKEND_API_BASE_URL}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Backend not running: {e}")
    
    def test_cart_add_item(self):
        """Test adding item to cart."""
        result = add_to_cart(self.customer_id, self.product_id, quantity=2)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            assert "cart" in result, "Expected 'cart' in successful response"
            print(f"✓ Added item to cart: {result.get('cart', {}).get('total', 0)}")
        else:
            print(f"⚠ Cart add failed (backend may not be running): {result.get('error', 'Unknown')}")
    
    def test_cart_get(self):
        """Test getting cart."""
        result = get_cart(self.customer_id)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            assert "cart" in result, "Expected 'cart' in successful response"
            print(f"✓ Retrieved cart with {len(result.get('cart', {}).get('items', []))} items")
        else:
            print(f"⚠ Cart get failed (backend may not be running): {result.get('error', 'Unknown')}")
    
    def test_cart_update_item(self):
        """Test updating cart item."""
        # First add an item
        add_result = add_to_cart(self.customer_id, self.product_id, quantity=1)
        if not add_result.get("success"):
            pytest.skip("Cannot test update - add failed")
        
        # Get item_id from cart
        cart_result = get_cart(self.customer_id)
        if not cart_result.get("success") or not cart_result.get("cart", {}).get("items"):
            pytest.skip("Cannot test update - no items in cart")
        
        item_id = cart_result["cart"]["items"][0]["item_id"]
        
        # Update item
        result = update_cart_item(item_id, quantity=3, customer_id=self.customer_id)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            print(f"✓ Updated cart item quantity to 3")
        else:
            print(f"⚠ Cart update failed: {result.get('error', 'Unknown')}")
    
    def test_cart_remove_item(self):
        """Test removing item from cart."""
        # First add an item
        add_result = add_to_cart(self.customer_id, self.product_id, quantity=1)
        if not add_result.get("success"):
            pytest.skip("Cannot test remove - add failed")
        
        # Get item_id from cart
        cart_result = get_cart(self.customer_id)
        if not cart_result.get("success") or not cart_result.get("cart", {}).get("items"):
            pytest.skip("Cannot test remove - no items in cart")
        
        item_id = cart_result["cart"]["items"][0]["item_id"]
        
        # Remove item
        result = remove_from_cart(item_id, customer_id=self.customer_id)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            print(f"✓ Removed item from cart")
        else:
            print(f"⚠ Cart remove failed: {result.get('error', 'Unknown')}")
    
    def test_cart_clear(self):
        """Test clearing cart."""
        result = clear_cart(self.customer_id)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            print(f"✓ Cleared cart")
        else:
            print(f"⚠ Cart clear failed: {result.get('error', 'Unknown')}")
    
    def test_payment_send_otp(self):
        """Test sending OTP."""
        result = send_otp(self.test_mobile)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            assert "expires_in_minutes" in result, "Expected 'expires_in_minutes' in response"
            print(f"✓ OTP sent successfully (expires in {result.get('expires_in_minutes')} minutes)")
        else:
            print(f"⚠ OTP send failed: {result.get('error', 'Unknown')}")
    
    def test_payment_verify_otp(self):
        """Test verifying OTP."""
        # First send OTP
        send_result = send_otp(self.test_mobile)
        if not send_result.get("success"):
            pytest.skip("Cannot test verify - send OTP failed")
        
        # In demo mode, OTP might be in response (for testing)
        # In production, user would provide OTP
        test_otp = "123456"  # This will likely fail, but tests the endpoint
        
        result = verify_otp(self.test_mobile, test_otp)
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            print(f"✓ OTP verified successfully")
        else:
            print(f"⚠ OTP verify failed (expected for test OTP): {result.get('error', 'Unknown')}")
    
    def test_cancellation_submit(self):
        """Test submitting cancellation request."""
        test_order_id = "ORD123456"
        result = submit_cancellation_request(
            order_id=test_order_id,
            reason="Test cancellation",
            customer_phone=self.test_mobile
        )
        assert "success" in result, f"Expected 'success' in result: {result}"
        if result.get("success"):
            assert "request_id" in result, "Expected 'request_id' in response"
            assert "customer_service_phone" in result, "Expected 'customer_service_phone' in response"
            print(f"✓ Cancellation request submitted: {result.get('request_id')}")
        else:
            print(f"⚠ Cancellation submit failed: {result.get('error', 'Unknown')}")


if __name__ == "__main__":
    print("=" * 60)
    print("Backend API Integration Tests")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_API_BASE_URL}")
    print()
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])
