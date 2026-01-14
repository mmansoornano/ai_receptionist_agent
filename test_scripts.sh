#!/bin/bash
# Quick test scripts for backend API integration

echo "=========================================="
echo "Backend API Integration Test Scripts"
echo "=========================================="
echo ""

# Check if backend is running
echo "1. Checking backend connection..."
BACKEND_URL="${BACKEND_API_BASE_URL:-http://localhost:8000}"
if curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
    echo "   ✓ Backend is running at $BACKEND_URL"
else
    echo "   ✗ Backend is not accessible at $BACKEND_URL"
    echo "   Please start the backend server first!"
    exit 1
fi

echo ""
echo "2. Running manual tests..."
python tests/manual_test.py

echo ""
echo "3. Running agent flow tests..."
python tests/test_agent_flow.py

echo ""
echo "=========================================="
echo "All tests complete!"
echo "=========================================="
