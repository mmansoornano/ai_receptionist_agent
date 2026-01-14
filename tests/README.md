# Testing Guide

This directory contains test scripts for verifying the backend API integration.

## Test Files

1. **`manual_test.py`** - Simple manual test script (no pytest required)
2. **`test_backend_integration.py`** - Comprehensive pytest-based integration tests
3. **`test_agent_flow.py`** - Tests the complete agent flow with LangGraph
4. **`run_all_tests.py`** - Runs all test suites and shows results

## Quick Start

### Option 1: Manual Testing (No Dependencies)

```bash
# Make sure backend is running
python tests/manual_test.py
```

This will test:
- Backend connection
- Cart operations (add, get, clear)
- Payment operations (send OTP, verify OTP)
- Cancellation operations

### Option 2: Automated Testing with pytest

```bash
# Install pytest if not already installed
pip install pytest

# Run backend integration tests
python -m pytest tests/test_backend_integration.py -v

# Run all tests
python tests/run_all_tests.py
```

### Option 3: Test Agent Flow

```bash
# Test the complete agent flow
python tests/test_agent_flow.py
```

## Prerequisites

1. **Backend Server Running**
   - Make sure your backend API is running
   - Default URL: `http://localhost:8000`
   - Can be changed via `BACKEND_API_BASE_URL` in `.env`

2. **Environment Setup**
   ```bash
   # Activate conda environment
   conda activate agent
   
   # Install dependencies
   pip install -r requirements.txt
   ```

## Test Results Interpretation

### ✓ Success
- Test passed successfully
- Backend API responded correctly

### ⚠ Warning
- Test completed but with expected issues (e.g., wrong OTP for verification)
- Backend may not be fully configured

### ✗ Failure
- Test failed
- Check:
  - Is backend running?
  - Is `BACKEND_API_BASE_URL` correct?
  - Are backend endpoints implemented correctly?

## Example Test Output

```
======================================================================
BACKEND API INTEGRATION - MANUAL TEST SUITE
======================================================================

Backend URL: http://localhost:8000

======================================================================
Backend Connection Test
======================================================================
Testing connection to: http://localhost:8000
✓ Backend is accessible (Status: 200)

======================================================================
Cart Operations Test
======================================================================

1. Adding protein-bar-white-chocolate to cart...
   ✓ Added successfully! Cart total: Rs.900.00
   Cart ID: test_customer_123
   Items: 1

2. Retrieving cart for customer test_customer_123...
   ✓ Retrieved successfully!
   Total items: 1
   Cart total: Rs.900.00
   - White Chocolate Brownie Protein Bar: 2x = Rs.900.00

3. Clearing cart...
   ✓ Cart cleared successfully!
```

## Troubleshooting

### Backend Connection Errors

If you see connection errors:
1. Check if backend is running: `curl http://localhost:8000/health`
2. Verify `BACKEND_API_BASE_URL` in `.env` or `config.py`
3. Check firewall/network settings

### 500 Internal Server Error

If backend returns 500 errors:
1. Check backend logs for errors
2. Verify backend endpoints match the API specification
3. Check database connectivity (if backend uses database)

### Import Errors

If you see import errors:
1. Make sure you're in the project root directory
2. Activate the conda environment: `conda activate agent`
3. Install dependencies: `pip install -r requirements.txt`

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with pytest (exits with code 0 on success)
python -m pytest tests/test_backend_integration.py -v --tb=short
```
