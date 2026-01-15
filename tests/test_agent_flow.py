"""Test agent flow with backend integration."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.main import receptionist_graph
from graph.state import ReceptionistState
from langchain_core.messages import HumanMessage
import json


def test_agent_flow():
    """Test complete agent flow."""
    print("=" * 60)
    print("Agent Flow Integration Test")
    print("=" * 60)
    print()
    
    # Test 1: Product Inquiry
    print("Test 1: Product Inquiry")
    print("-" * 60)
    state1: ReceptionistState = {
        "messages": [HumanMessage(content="What is the price of protein bars?")],
        "intent": None,
        "conversation_context": None,
        "customer_info": None,
        "cart_data": None,
        "order_data": None,
        "payment_data": None,
        "channel": "sms",
        "language": "en",
        "conversation_id": "test_conv_1",
        "customer_id": "test_customer"
    }
    
    try:
        result1 = receptionist_graph.invoke(state1)
        last_message = result1["messages"][-1]
        print(f"Response: {last_message.content[:200]}...")
        print("✓ Product inquiry test passed")
    except Exception as e:
        print(f"✗ Product inquiry test failed: {e}")
    print()
    
    # Test 2: Ordering (Add to Cart)
    print("Test 2: Ordering - Add to Cart")
    print("-" * 60)
    state2: ReceptionistState = {
        "messages": [HumanMessage(content="Add 2 white chocolate protein bars to my cart")],
        "intent": None,
        "conversation_context": None,
        "customer_info": None,
        "cart_data": None,
        "order_data": None,
        "payment_data": None,
        "channel": "sms",
        "language": "en",
        "conversation_id": "test_conv_2",
        "customer_id": "test_customer"
    }
    
    try:
        result2 = receptionist_graph.invoke(state2)
        last_message = result2["messages"][-1]
        print(f"Response: {last_message.content[:200]}...")
        print("✓ Ordering test passed")
    except Exception as e:
        print(f"✗ Ordering test failed: {e}")
    print()
    
    # Test 3: View Cart
    print("Test 3: View Cart")
    print("-" * 60)
    state3: ReceptionistState = {
        "messages": [HumanMessage(content="Show me my cart")],
        "intent": None,
        "conversation_context": None,
        "customer_info": None,
        "cart_data": None,
        "order_data": None,
        "payment_data": None,
        "channel": "sms",
        "language": "en",
        "conversation_id": "test_conv_3",
        "customer_id": "test_customer"
    }
    
    try:
        result3 = receptionist_graph.invoke(state3)
        last_message = result3["messages"][-1]
        print(f"Response: {last_message.content[:200]}...")
        print("✓ View cart test passed")
    except Exception as e:
        print(f"✗ View cart test failed: {e}")
    print()
    
    print("=" * 60)
    print("Agent Flow Tests Complete")
    print("=" * 60)


if __name__ == "__main__":
    test_agent_flow()
