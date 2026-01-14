"""Manual test script for backend API integration."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.cart_service import add_to_cart, get_cart, clear_cart
from services.payment_service import send_otp, verify_otp, confirm_payment
from services.cancellation_service import submit_cancellation_request
from config import BACKEND_API_BASE_URL
import requests


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def test_backend_connection():
    """Test if backend is accessible."""
    print_section("Backend Connection Test")
    print(f"Testing connection to: {BACKEND_API_BASE_URL}")
    
    try:
        # Try to reach backend
        response = requests.get(f"{BACKEND_API_BASE_URL}/health", timeout=5)
        print(f"✓ Backend is accessible (Status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to backend at {BACKEND_API_BASE_URL}")
        print("  Make sure the backend server is running!")
        return False
    except Exception as e:
        print(f"⚠ Backend health check failed: {e}")
        print("  Backend may be running but health endpoint not available")
        return True  # Continue tests anyway


def test_cart_operations():
    """Test cart operations."""
    print_section("Cart Operations Test")
    
    customer_id = "test_customer_123"
    product_id = "protein-bar-white-chocolate"
    
    # Test 1: Add to cart
    print(f"\n1. Adding {product_id} to cart...")
    result = add_to_cart(customer_id, product_id, quantity=2)
    if result.get("success"):
        cart = result.get("cart", {})
        print(f"   ✓ Added successfully! Cart total: Rs.{cart.get('total', 0):.2f}")
        print(f"   Cart ID: {cart.get('cart_id', 'N/A')}")
        print(f"   Items: {len(cart.get('items', []))}")
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        return
    
    # Test 2: Get cart
    print(f"\n2. Retrieving cart for customer {customer_id}...")
    result = get_cart(customer_id)
    if result.get("success"):
        cart = result.get("cart", {})
        print(f"   ✓ Retrieved successfully!")
        print(f"   Total items: {len(cart.get('items', []))}")
        print(f"   Cart total: Rs.{cart.get('total', 0):.2f}")
        for item in cart.get('items', []):
            print(f"   - {item.get('name')}: {item.get('quantity')}x = Rs.{item.get('subtotal', 0):.2f}")
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
    
    # Test 3: Clear cart
    print(f"\n3. Clearing cart...")
    result = clear_cart(customer_id)
    if result.get("success"):
        print(f"   ✓ Cart cleared successfully!")
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")


def test_payment_operations():
    """Test payment operations."""
    print_section("Payment Operations Test")
    
    mobile_number = "03001234567"
    
    # Test 1: Send OTP
    print(f"\n1. Sending OTP to {mobile_number}...")
    result = send_otp(mobile_number)
    if result.get("success"):
        print(f"   ✓ OTP sent successfully!")
        print(f"   Expires in: {result.get('expires_in_minutes', 'N/A')} minutes")
        # In demo mode, OTP might be in response
        if 'otp' in result:
            print(f"   OTP (demo): {result['otp']}")
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")
        return
    
    # Test 2: Verify OTP (will likely fail with wrong OTP, but tests endpoint)
    print(f"\n2. Verifying OTP...")
    test_otp = "123456"  # This will likely fail
    result = verify_otp(mobile_number, test_otp)
    if result.get("success"):
        print(f"   ✓ OTP verified successfully!")
    else:
        print(f"   ⚠ Expected failure (test OTP): {result.get('error', 'Unknown error')}")
    
    # Note: Payment confirmation requires verified OTP, so skipping for now


def test_cancellation_operations():
    """Test cancellation operations."""
    print_section("Cancellation Operations Test")
    
    order_id = "ORD123456"
    reason = "Test cancellation request"
    customer_phone = "03001234567"
    
    print(f"\n1. Submitting cancellation request for order {order_id}...")
    result = submit_cancellation_request(order_id, reason, customer_phone)
    if result.get("success"):
        print(f"   ✓ Cancellation request submitted successfully!")
        print(f"   Request ID: {result.get('request_id', 'N/A')}")
        print(f"   Customer Service: {result.get('customer_service_phone', 'N/A')}")
    else:
        print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")


def main():
    """Run all manual tests."""
    print("\n" + "=" * 70)
    print("BACKEND API INTEGRATION - MANUAL TEST SUITE")
    print("=" * 70)
    print(f"\nBackend URL: {BACKEND_API_BASE_URL}")
    print("\nNote: Some tests may fail if backend is not running or has errors.")
    print("      This is expected and helps identify integration issues.\n")
    
    # Test backend connection
    backend_available = test_backend_connection()
    
    if not backend_available:
        print("\n⚠ Backend not accessible. Some tests will be skipped.")
        print("  Please start the backend server and try again.")
        return
    
    # Run tests
    try:
        test_cart_operations()
    except Exception as e:
        print(f"\n✗ Cart operations test failed with exception: {e}")
    
    try:
        test_payment_operations()
    except Exception as e:
        print(f"\n✗ Payment operations test failed with exception: {e}")
    
    try:
        test_cancellation_operations()
    except Exception as e:
        print(f"\n✗ Cancellation operations test failed with exception: {e}")
    
    print_section("Test Suite Complete")
    print("\nAll tests completed. Check results above for any failures.")
    print("\nTo run automated tests with pytest:")
    print("  python -m pytest tests/test_backend_integration.py -v")


if __name__ == "__main__":
    main()
