"""Run all tests and show results."""
import sys
from pathlib import Path
import subprocess
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BACKEND_API_BASE_URL
import requests


def check_backend_health():
    """Check if backend is running."""
    print("Checking backend health...")
    try:
        # Try common health check endpoints
        endpoints = ["/health", "/api/health", "/"]
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BACKEND_API_BASE_URL}{endpoint}", timeout=3)
                if response.status_code == 200:
                    print(f"✓ Backend is accessible at {BACKEND_API_BASE_URL}")
                    return True
            except:
                continue
        print(f"⚠ Backend may not be running at {BACKEND_API_BASE_URL}")
        print("  Some tests may fail or be skipped")
        return False
    except Exception as e:
        print(f"⚠ Cannot reach backend: {e}")
        return False


def run_tests():
    """Run all test suites."""
    print("=" * 70)
    print("BACKEND API INTEGRATION TEST SUITE")
    print("=" * 70)
    print()
    print(f"Backend URL: {BACKEND_API_BASE_URL}")
    print()
    
    # Check backend health
    backend_available = check_backend_health()
    print()
    
    # Run backend integration tests
    print("=" * 70)
    print("Running Backend Integration Tests")
    print("=" * 70)
    print()
    
    test_file = Path(__file__).parent / "test_backend_integration.py"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "-s", "--tb=short"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    if result.returncode == 0:
        print("✓ All tests passed!")
    else:
        print(f"⚠ Some tests failed or were skipped (exit code: {result.returncode})")
        if not backend_available:
            print("  Note: Backend may not be running - some failures are expected")
    
    print()
    print("=" * 70)
    print("Agent Flow Tests")
    print("=" * 70)
    print()
    
    # Run agent flow tests
    flow_test_file = Path(__file__).parent / "test_agent_flow.py"
    try:
        subprocess.run([sys.executable, str(flow_test_file)], check=False)
    except Exception as e:
        print(f"Error running agent flow tests: {e}")
    
    print()
    print("=" * 70)
    print("Test Suite Complete")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
