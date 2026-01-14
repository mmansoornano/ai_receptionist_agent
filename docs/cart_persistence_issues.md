# Cart Persistence and Payment Flow Issues

## Issue 1: Cart Persistence

### Problem
The shopping cart is not persistent across requests/sessions.

### Root Causes

1. **Default `customer_id` Usage:**
   - All cart tools use `customer_id="anonymous"` as default
   - Each request might use a different `customer_id` or default to "anonymous"
   - This means different carts for different sessions/users

2. **Customer ID Not Passed to Tools:**
   - The state has `customer_id` but tools don't receive it from the state
   - Tools use hardcoded default "anonymous" instead of state's `customer_id`
   - The state's `customer_id` is not being used consistently

3. **Backend Storage:**
   - The cart is stored in the backend API (good)
   - But if `customer_id` is not consistent, the backend can't retrieve the same cart
   - Backend needs to persist carts by `customer_id` properly

### Current Behavior

**Cart Tools:**
```python
# All tools default to "anonymous"
def add_item_to_cart(product_id: str, quantity: int = 1, customer_id: str = "anonymous") -> str:
def view_cart(customer_id: str = "anonymous") -> str:
```

**State:**
```python
class ReceptionistState(TypedDict):
    customer_id: Optional[str]  # Available but not used by tools
```

### Expected Behavior

1. **Use State's `customer_id`:**
   - Tools should use `customer_id` from state, not hardcoded defaults
   - If `customer_id` is None, generate or use a session-based ID
   - Use the same `customer_id` consistently across the conversation

2. **Backend Persistence:**
   - Backend should store carts by `customer_id` in database
   - Cart should persist across sessions if same `customer_id` is used
   - Backend should return the same cart for the same `customer_id`

## Issue 2: Cart Data in Payment Flow

### Problem
The payment agent doesn't fetch cart data before creating an order.

### Current Flow

**Payment Agent System Prompt:**
```
6. Create order using create_order_from_cart tool with cart data and transaction ID
```

**Payment Tool:**
```python
def create_order_from_cart(cart_data: dict, transaction_id: str) -> str:
    """Create order after payment confirmation.
    
    Args:
        cart_data: Cart data dictionary with items and total
        transaction_id: Payment transaction ID
    """
```

### Issues

1. **No Cart Fetching Tool:**
   - Payment agent has no way to fetch cart data
   - `create_order_from_cart` requires `cart_data` but there's no tool to get it
   - The LLM can't provide cart data - it needs to be fetched from the backend

2. **Missing Step in Payment Flow:**
   - Payment flow should: Get Cart → Send OTP → Verify OTP → Confirm Payment → Create Order
   - Currently missing: "Get Cart" step
   - Payment agent needs access to cart tools or a way to get cart data

3. **Cart Data Should Come from Backend:**
   - Cart data should be fetched from backend API using `customer_id`
   - Should not rely on LLM to provide cart data
   - Should fetch fresh cart data before creating order

### Expected Behavior

1. **Add Cart Fetching to Payment Flow:**
   - Payment agent should fetch cart before creating order
   - Use `customer_id` from state to fetch cart
   - Get cart total for payment amount
   - Use cart data for order creation

2. **Payment Flow Should Be:**
   ```
   1. Get cart using customer_id (get total amount)
   2. Request mobile number
   3. Send OTP
   4. Verify OTP
   5. Confirm payment with amount from cart
   6. Create order with cart data and transaction ID
   ```

3. **Options:**
   - Option A: Add cart tools to payment agent (get_cart tool)
   - Option B: Create a dedicated payment flow tool that handles cart fetching
   - Option C: Fetch cart in the payment tool itself (before creating order)

## Recommendations

### For Cart Persistence:

1. **Use State's `customer_id`:**
   - Modify cart tools to use `customer_id` from state
   - If `customer_id` is None, use `phone_number` or generate a session ID
   - Pass `customer_id` from state to tools (requires tool modifications or context passing)

2. **Backend Requirements:**
   - Backend should persist carts in database by `customer_id`
   - Backend should handle "anonymous" carts (session-based or temporary)
   - Backend should return the same cart for the same `customer_id`

### For Payment Flow:

1. **Add Cart Fetching:**
   - Add `get_cart` tool to payment agent tools (or share cart tools)
   - Fetch cart before creating order
   - Use cart total for payment amount
   - Use cart data for order creation

2. **Alternative: Create Payment Flow Tool:**
   - Create a `process_payment_with_cart` tool that:
     - Fetches cart using `customer_id`
     - Gets cart total
     - Processes payment flow
     - Creates order with cart data

3. **Update Payment Agent System Prompt:**
   - Update to include cart fetching step
   - Clarify that cart should be fetched before payment confirmation
   - Specify that cart data comes from backend API

## Related Files

- `services/cart_service.py` - Cart API calls
- `tools/cart_tool.py` - Cart tools (use "anonymous" default)
- `tools/payment_tool.py` - Payment tools (requires cart_data parameter)
- `graph/payment_agent.py` - Payment agent (doesn't fetch cart)
- `graph/state.py` - State schema (has customer_id)
- `main.py` - Entry point (passes customer_id to state)
