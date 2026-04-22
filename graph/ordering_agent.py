"""Ordering agent for managing shopping cart and orders."""
import json
import time
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.types import Command
from config import DEFAULT_LANGUAGE, LLM_PROVIDER, OLLAMA_MODEL
from services.llm_service import get_llm_service
from services.prompt_loader import get_prompt
from services.product_service import list_products
from graph.state import ReceptionistState
from tools.cart_tool import CART_TOOLS
from tools.product_tool import PRODUCT_TOOLS
from tools.calculator_tool import CALCULATOR_TOOLS
from langgraph.prebuilt import ToolNode
from utils.logger import log_agent_flow, log_llm_call, log_prompt, log_graph_flow
from utils.conversation_history import format_conversation_history
from utils.message_utils import create_message_update_command
from utils.message_filtering import filter_messages_for_agent, get_last_human_message
from utils.llm_retry import invoke_with_retry
from utils.error_handler import handle_llm_error


def _cart_tool_messages_show_backend_failure(messages: list) -> bool:
    """True when recent cart/product tool results indicate the backend was unreachable or errored."""
    cartish = (
        "add_item_to_cart",
        "add_items_to_cart_batch",
        "view_cart",
        "remove_item_from_cart",
        "update_cart_quantity",
        "clear_shopping_cart",
        "list_all_products",
    )
    fail_markers = (
        "connection refused",
        "max retries exceeded",
        "success': false",
        "success\": false",
        '"success": false',
        "failed to establish",
        "errno 61",
        "error: http",
        "error: httpconnectionpool",
    )
    for msg in reversed(messages[-12:]):
        if not isinstance(msg, ToolMessage):
            continue
        name = (getattr(msg, "name", None) or "") or ""
        name = str(name)
        body_raw = str(msg.content) if msg.content is not None else ""
        body = body_raw.lower()
        is_cartish = any(c in name for c in cartish) or (
            not name.strip()
            and any(x in body for x in ("/api/cart", "/api/products", "cart_add", "product_list"))
        )
        if not is_cartish:
            continue
        if any(m in body for m in fail_markers):
            return True
        if body_raw.lstrip().lower().startswith("error:") and "http" in body:
            return True
    return False


def get_max_tokens_for_model():
    """Get appropriate max_tokens limit based on the configured model.
    
    Returns:
        int: Maximum tokens to use for message trimming
    """
    if LLM_PROVIDER == 'ollama':
        model = OLLAMA_MODEL.lower()
        # Llama 3.2 8B supports 128K context window
        if 'llama3.2' in model or 'llama3.1' in model:
            # Use 100K for input, leaving 28K for response (plenty of room)
            return 100000
        # Default for other Ollama models (conservative)
        return 32000
    elif LLM_PROVIDER == 'openai':
        # OpenAI models typically have 128K-200K context windows
        # Use 100K for input, leaving room for response
        return 100000
    else:
        # Conservative default
        return 32000


def ordering_agent(state: ReceptionistState) -> Command | ReceptionistState:
    """Ordering agent that handles cart management."""
    from langchain_core.messages import HumanMessage
    
    log_graph_flow("ordering_agent", "Entering Node")
    # Combine cart tools, product tools, and calculator tools for ordering agent
    ORDERING_TOOLS = (CART_TOOLS or []) + (PRODUCT_TOOLS or []) + (CALCULATOR_TOOLS or [])
    
    log_agent_flow("ORDERING", "Agent Invoked", {
        "tools_count": len(ORDERING_TOOLS),
        "tools": [tool.name for tool in ORDERING_TOOLS]
    })
    
    messages = state.get("messages", [])
    language = state.get("language", DEFAULT_LANGUAGE)
    
    # Filter messages before processing (includes ToolMessages so LLM can see tool results like product lists)
    # This allows the agent to reference product information from list_all_products without calling it again
    filtered_messages = filter_messages_for_agent(messages, include_system=True, include_tool_results=True)
    last_human_message = get_last_human_message(messages)
    
    # Check if user message indicates completion/finalization (dynamic intent detection)
    # If so, update intent to "payment" for direct transition
    current_intent = state.get("intent", "ordering")
    if last_human_message:
        msg_lower = last_human_message.content.lower() if last_human_message.content else ""
        completion_phrases = ["thats all", "that's all", "finalize", "finalise", "complete", "done", "ready", "let's finalize", "lets finalize", "finalize the order", "no i don't want to add", "no more"]
        has_cart_context = any(word in " ".join([str(m.content) for m in messages[-10:]]).lower() for word in ["cart", "order", "add", "item"])
        
        if has_cart_context and any(phrase in msg_lower for phrase in completion_phrases):
            # Update intent to payment for direct transition
            current_intent = "payment"
            log_agent_flow("ORDERING", "Intent transition detected: ordering -> payment", {"trigger": msg_lower})
    
    # Get prompt and create system message
    ordering_prompt = get_prompt("ordering_agent")
    
    # ALWAYS check for list_all_products tool results and append to prompt
    tool_result_content = None
    has_product_tool_results = False
    
    # Check if list_all_products was called (look for AIMessage with tool_calls)
    list_all_products_called = False
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get('name', '') if isinstance(tc, dict) else getattr(tc, 'name', '')
                if tool_name == 'list_all_products':
                    list_all_products_called = True
                    break
            if list_all_products_called:
                break
    
    # Debug: Log all message types to understand what's in state
    message_types = [type(msg).__name__ for msg in messages]
    tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]
    log_agent_flow("ORDERING", "Checking for tool results", {
        "total_messages": len(messages),
        "message_types": message_types[-10:],  # Last 10 message types
        "tool_message_count": len(tool_messages),
        "list_all_products_called": list_all_products_called,
        "last_5_message_types": message_types[-5:] if len(message_types) >= 5 else message_types
    })
    
    # Check ALL messages for tool results (check in reverse to get most recent)
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            # Debug log each ToolMessage
            content_preview = str(msg.content)[:100] if hasattr(msg, 'content') and msg.content else "No content"
            log_agent_flow("ORDERING", "Found ToolMessage", {
                "has_content": hasattr(msg, 'content') and bool(msg.content),
                "content_preview": content_preview,
                "tool_call_id": getattr(msg, 'tool_call_id', None)
            })
            
            if hasattr(msg, 'content') and msg.content:
                content_str = str(msg.content)
                # More lenient check - if it has PKR and looks like a product list, use it
                # Check for product catalog marker OR product-related keywords
                is_product_catalog = (
                    'PRODUCT CATALOG' in content_str or 
                    ('PKR' in content_str and len(content_str) > 100) or  # Has PKR and substantial content
                    'cookie' in content_str.lower() or
                    'protein' in content_str.lower() or
                    'granola' in content_str.lower() or
                    'gift box' in content_str.lower()
                )
                
                if is_product_catalog:
                    tool_result_content = content_str
                    has_product_tool_results = True
                    log_agent_flow("ORDERING", "Product catalog ToolMessage found!", {
                        "content_length": len(content_str),
                        "has_product_catalog_marker": 'PRODUCT CATALOG' in content_str,
                        "content_preview": content_str[:300]
                    })
                    break
    
    # FALLBACK: If tool was called but result not found, fetch directly from service
    if list_all_products_called and not has_product_tool_results:
        log_agent_flow("ORDERING", "Tool was called but result not found - fetching directly from service", {})
        try:
            from tools.product_tool import list_all_products
            tool_result_content = list_all_products.invoke({})
            has_product_tool_results = True
            log_agent_flow("ORDERING", "Fetched product catalog directly from service", {
                "content_length": len(tool_result_content) if tool_result_content else 0
            })
        except Exception as e:
            log_agent_flow("ORDERING", "Failed to fetch products directly", {"error": str(e)})
    
    # Check if user is asking for products or wants to order (not just adding items)
    user_asking_for_products = False
    if last_human_message and last_human_message.content:
        user_msg_lower = str(last_human_message.content).lower()
        user_asking_for_products = any(phrase in user_msg_lower for phrase in [
            'show products', 'list products', 'what products', 'available products',
            'product catalog', 'catalog', 'menu', 'what do you have', 'what can i order',
            'i want to order', 'want to order', "i'd like to order", 'like to order',
            'want to buy', 'i want to buy', 'help me order', 'ready to order'
        ])
    
    # Format conversation history first to check if catalog is already shown
    conversation_history = format_conversation_history(messages, max_messages=10)  # Use full messages for history
    
    # Check if product catalog is already in recent conversation history (to avoid duplication)
    catalog_already_shown = False
    if conversation_history:
        catalog_already_shown = 'PRODUCT CATALOG' in conversation_history or (tool_result_content and tool_result_content[:100] in conversation_history)
    
    # Check if user is adding items BEFORE deciding what to inject
    user_adding_items_check = False
    if last_human_message and last_human_message.content:
        user_msg_lower_check = str(last_human_message.content).lower()
        user_adding_items_check = any(phrase in user_msg_lower_check for phrase in [
            'add', 'to cart', 'add to cart', 'add item', 'add product'
        ])
    
    # Only append product list to prompt if found AND not already in conversation history
    # Always inject full catalog when user asks for products, even if they're also adding items
    if has_product_tool_results and tool_result_content and not catalog_already_shown:
        # Count products in the tool result for verification
        product_count = tool_result_content.count('\n- ')  # Count product lines
        log_agent_flow("ORDERING", "Product catalog found - appending to prompt", {
            "tool_result_length": len(tool_result_content),
            "estimated_product_count": product_count,
            "catalog_already_shown": catalog_already_shown,
            "user_asking_for_products": user_asking_for_products,
            "user_adding_items": user_adding_items_check
        })
        
        # APPEND THE FULL PRODUCT LIST DIRECTLY TO THE PROMPT - THIS IS THE SOURCE OF TRUTH
        # Show full catalog with display instructions if user is asking for products
        if user_asking_for_products:
            ordering_prompt += f"""

═══════════════════════════════════════════════════════════════════════════════
CRITICAL - COMPLETE PRODUCT CATALOG (FROM list_all_products TOOL):
═══════════════════════════════════════════════════════════════════════════════

{tool_result_content}

═══════════════════════════════════════════════════════════════════════════════

MANDATORY INSTRUCTIONS (USER IS ASKING FOR PRODUCTS):
1. You MUST show ALL products from the catalog above - EVERY SINGLE PRODUCT
2. Do NOT summarize - show the COMPLETE list
3. Do NOT show only some products - show ALL products
4. Do NOT make up or hallucinate products - use ONLY what's in the catalog above
5. Count the products: There are {product_count} products in the catalog above - you MUST show all {product_count} products
6. Use the EXACT product names and prices as shown in the catalog above
7. When presenting products to the user, format them exactly as shown above with categories and prices

The product catalog above is the ONLY source of truth for product information.
═══════════════════════════════════════════════════════════════════════════════
"""
        elif user_adding_items_check:
            # User is ONLY adding items - provide product ID mapping so LLM uses correct IDs
            # Fetch fresh product list for ID mapping
            try:
                from services.product_service import list_products as fetch_products
                products = fetch_products()
                product_id_mapping = []
                for p in products:
                    pid = p.get('product_id', '')
                    pname = p.get('name', '')
                    if pid and pname:
                        product_id_mapping.append(f"- {pname} -> product_id: \"{pid}\"")
                
                if product_id_mapping:
                    mapping_text = '\n'.join(product_id_mapping)
                    ordering_prompt += f"""

PRODUCT ID MAPPING – use ONLY these EXACT product_id values for add_item_to_cart / add_items_to_cart_batch:
{mapping_text}

COMMON MISTAKES – use the CORRECT id on the right, NEVER the wrong one:
- Crunchy Choco Grain Granola Bar: use "granola-bar-crunchy" (NOT granola-bar-crunchy-choco-grain, crunchy-choco-grain-granola-bar)
- White Chocolate Brownie Protein Bar: use "protein-bar-white-chocolate" (NOT protein-bar-white-chocolate-brownie)
- Almond Brownie Protein Bar: use "protein-bar-almond" (NOT protein-bar-almond-brownie)
- Chocolate Chunks Cookie: use "cookie-chocolate" (NOT cookie-chocolate-chunks, chocolate-chunks-cookie)
- Chocolate & Peanut Butter Granola Bar: use "granola-bar-chocolate-pb" (NOT granola-bar-chocolate-peanut-butter)
- Coffee & Pumpkin Seed Granola Bar: use "granola-bar-coffee-pumpkin" (NOT granola-bar-coffee-pumpkin-seed)
- Peanut Butter Cookie: use "cookie-pb" (NOT cookie-peanut-butter, peanut-butter-cookie)
- Peanut Butter Fudge Protein Bar: use "protein-bar-peanut-butter" (NOT protein-bar-peanut-butter-fudge)
- Chocolate & Walnut Granola Bar: use "granola-bar-chocolate-walnut" (NOT chocolate-walnut-granola-bar)

USER IS ADDING ITEMS:
1. If MULTIPLE items: call add_items_to_cart_batch once with items_json = [{{"product_id": "...", "quantity": N}}, ...]. If SINGLE item: call add_item_to_cart. Use EXACT product_ids from the mapping above only.
2. Call view_cart after adding.
3. Show cart contents - DO NOT show product catalog.
"""
            except Exception as e:
                log_agent_flow("ORDERING", "Failed to fetch product ID mapping", {"error": str(e)})
                ordering_prompt += """

USER IS ADDING ITEMS - DO NOT show catalog. Just call tools and show cart.
"""
        else:
            # User is NOT asking for products and NOT adding items - provide full catalog as reference
            ordering_prompt += f"""

═══════════════════════════════════════════════════════════════════════════════
PRODUCT CATALOG REFERENCE (FROM list_all_products TOOL):
═══════════════════════════════════════════════════════════════════════════════

{tool_result_content}

═══════════════════════════════════════════════════════════════════════════════

IMPORTANT: The catalog above is for REFERENCE ONLY. Use it to:
- Get EXACT product names and prices when user mentions products
- Verify product names match exactly (e.g., "Chocolate Chunks Cookie" not "Cookie Chocolate")
- Use correct prices (e.g., PKR 200.00 not Rs. 80)

DO NOT show the full catalog unless the user explicitly asks for it.
When user is adding items to cart, just add the item - don't show the catalog again.
═══════════════════════════════════════════════════════════════════════════════
"""
    else:
        log_agent_flow("ORDERING", "No product catalog tool results found", {
            "messages_count": len(messages),
            "tool_messages_count": sum(1 for m in messages if isinstance(m, ToolMessage))
        })

    # User wants to order but we have no product tool results yet: force list_all_products first
    if user_asking_for_products and not (has_product_tool_results and tool_result_content):
        ordering_prompt += """

CRITICAL: You MUST call list_all_products first. Do not list any products until you have the tool result.
Do not make up, guess, or hallucinate product names or prices. Respond only after calling the tool.
"""
    
    # Trim messages for token limits AFTER filtering (matches what LLM will see)
    # Remove end_on to preserve AIMessages with tool calls (end_on excludes them)
    # Use model-specific token limits (llama3.2:8b supports 128K, so we use 100K for input)
    max_tokens_limit = get_max_tokens_for_model()
    trimmed_messages = trim_messages(
        filtered_messages,  # Use filtered messages instead of raw messages
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens_limit,  # Use model-specific limit (100K for llama3.2:8b)
        start_on="human",
        include_system=False,
        allow_partial=False
    )
    log_agent_flow("ORDERING", "Message trimming", {
        "max_tokens_limit": max_tokens_limit,
        "filtered_messages_count": len(filtered_messages),
        "trimmed_messages_count": len(trimmed_messages),
        "has_tool_results": has_product_tool_results
    })
    
    # conversation_history already created above - keep it minimal
    if conversation_history:
        # Limit conversation history to last 5 messages to reduce prompt size
        history_lines = conversation_history.split("\n")
        recent_history = "\n".join(history_lines[-20:])  # Last 20 lines max
        ordering_prompt += f"\n\nRecent conversation:\n{recent_history}"
    
    customer_id = state.get("customer_id")
    
    # Always use customer_id, never "anonymous"
    if customer_id:
        ordering_prompt += f"\n\nCustomer ID: {customer_id} - use this for all cart tools."
    else:
        ordering_prompt += "\n\nWARNING: No customer_id - using 'anonymous'."
        log_agent_flow("ORDERING", "No customer_id in state", {"using_anonymous": True})
    
    if _cart_tool_messages_show_backend_failure(messages):
        log_agent_flow("ORDERING", "Injecting backend-failure reply constraints (tool errors in context)", {})
        ordering_prompt += """

═══════════════════════════════════════════════════════════════════════════════
CRITICAL — CART / PRODUCT API ERRORS IN TOOL RESULTS (read the ToolMessage(s) above):
The shop backend or network call failed (connection error, timeout, or success=false).
- Do NOT claim items were added, do NOT list cart line items, PKR totals, or delivery fees from a cart.
- Do NOT ask the user to pay or "confirm" a cart you could not read.
- Reply in 1–3 short sentences: apologize, say the cart or product service is temporarily unavailable, and suggest trying again in a moment (or that the store systems may need to be online).
- You may acknowledge the product they asked for by name only; do not fabricate a successful add.
═══════════════════════════════════════════════════════════════════════════════
"""
    
    # Log the prompt being used
    log_prompt("ORDERING_AGENT", ordering_prompt, {
        "customer_id": customer_id,
        "current_intent": current_intent,
        "message_count": len(messages),
        "has_product_tool_results": has_product_tool_results
    })
    
    system_msg = SystemMessage(content=ordering_prompt)
    
    # Prepare messages with system prompt (trimmed messages already processed above)
    # Full message history remains in state - trimmed_messages are only for LLM context
    agent_messages = [system_msg] + trimmed_messages
    
    # Initialize LLM with tools
    start_time = time.time()
    llm_service = get_llm_service()
    llm = llm_service.get_llm(temperature=0.7)
    
    # Bind tools to LLM (if supported and tools available)
    if llm_service.supports_tools() and ORDERING_TOOLS:
        llm_with_tools = llm.bind_tools(ORDERING_TOOLS)
        log_agent_flow("ORDERING", "LLM with Tools", {"tools_bound": True, "tools": [tool.name for tool in ORDERING_TOOLS]})
    else:
        llm_with_tools = llm
        log_agent_flow("ORDERING", "LLM without Tools", {"tools_bound": False})
    
    # Get response from LLM with retry logic
    log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent")
    try:
        response = invoke_with_retry(
            llm=llm_with_tools,
            messages=agent_messages,
            max_retries=3,
            initial_delay=1.0,
            agent_name="ordering_agent"
        )
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent", response_time)
    except Exception as e:
        response_time = time.time() - start_time
        log_llm_call(llm_service.provider_name, llm_service.model_name, "Ordering Agent", response_time)
        return handle_llm_error(e, "ordering_agent", state)
    
    # Check if user is asking for products vs adding items
    # This check happens AFTER LLM response, so we can clean up the response if needed
    user_asking_for_products = False
    user_adding_items = False
    
    if last_human_message and last_human_message.content:
        user_msg_lower = str(last_human_message.content).lower()
        # User is adding items (explicit add commands) - check this FIRST as it's more specific
        user_adding_items = any(phrase in user_msg_lower for phrase in [
            'add', 'to cart', 'add to cart', 'add item', 'add product'
        ])
        # User is asking for products (only if NOT adding items)
        if not user_adding_items:
            user_asking_for_products = any(phrase in user_msg_lower for phrase in [
                'show products', 'list products', 'what products', 'available products', 
                'product catalog', 'catalog', 'menu', 'what do you have', 'what can i order',
                'i want to order', 'i want to see'
            ])
    
    # Check for tool calls and ensure view_cart is called after add_item_to_cart
    if hasattr(response, 'tool_calls') and response.tool_calls:
        tool_names = []
        for tc in response.tool_calls:
            if isinstance(tc, dict):
                tool_names.append(tc.get('name', 'unknown'))
            else:
                tool_names.append(getattr(tc, 'name', 'unknown'))
        
        has_add_item = any('add_item_to_cart' in name for name in tool_names)
        has_batch_add = any('add_items_to_cart_batch' in name for name in tool_names)
        has_view_cart = any('view_cart' in name for name in tool_names)
        
        log_agent_flow("ORDERING", "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": tool_names,
            "has_add_item": has_add_item,
            "has_batch_add": has_batch_add,
            "has_view_cart": has_view_cart
        })
        
        # If user is adding items and we called add (single or batch) but NOT view_cart, add view_cart call
        if user_adding_items and (has_add_item or has_batch_add) and not has_view_cart:
            # Add view_cart tool call
            customer_id = state.get('customer_id', 'anonymous')
            view_cart_tool_call = {
                'name': 'view_cart',
                'args': {'customer_id': customer_id},
                'id': f'view_cart_{int(time.time())}'
            }
            updated_tool_calls = list(response.tool_calls) + [view_cart_tool_call]
            response = AIMessage(
                content=response.content,
                tool_calls=updated_tool_calls,
                id=getattr(response, 'id', None)
            )
            log_agent_flow("ORDERING", "Added view_cart tool call after add_item/add_batch", {
                "customer_id": customer_id
            })
    
    # Only include catalog if user is asking for products AND NOT adding items
    # Use ONLY tool_result_content (PRODUCT CATALOG + === Category === + - Name: PKR) so frontend parses
    # Add/increment UI. Never use LLM output (numbered list, "Customer ID...") for product list.
    if has_product_tool_results and tool_result_content and user_asking_for_products and not user_adding_items:
        closing = "What would you like to order?"
        enhanced_content = f"{tool_result_content}\n\n{closing}"
        response = AIMessage(
            content=enhanced_content,
            tool_calls=getattr(response, 'tool_calls', None),
            id=getattr(response, 'id', None)
        )
        log_agent_flow("ORDERING", "Response set to canonical product catalog (tool format) for webchat Add/increment UI", {
            "user_asking_for_products": True
        })
    elif has_product_tool_results and user_adding_items:
        # User is adding items - check for cart tool results and use them instead of catalog
        response_content = response.content if hasattr(response, 'content') and response.content else ""
        
        # Check for cart tool results (view_cart, add_item_to_cart) in ALL messages
        # After tools execute, ToolMessages are added to state, so check all messages
        cart_tool_results = []
        view_cart_result = None
        
        # Look for ToolMessages from cart tools (check all messages, most recent first)
        for msg in reversed(messages):  # Check ALL messages, most recent first
            if isinstance(msg, ToolMessage) and hasattr(msg, 'content') and msg.content:
                content_str = str(msg.content)
                # Check if this is a view_cart result (most important - shows cart contents)
                # Look for patterns like "Cart Contents:", "Cart total:", etc.
                if ('cart contents' in content_str.lower() or 
                    ('cart' in content_str.lower() and 'total' in content_str.lower()) or
                    'qty:' in content_str.lower() or
                    ('items' in content_str.lower() and 'rs.' in content_str.lower())):
                    if view_cart_result is None:  # Keep most recent
                        view_cart_result = content_str
                        log_agent_flow("ORDERING", "Found view_cart result", {
                            "content_preview": content_str[:200]
                        })
                # Also collect add_item_to_cart results
                elif 'added' in content_str.lower() and 'to cart' in content_str.lower():
                    cart_tool_results.append(content_str)
        
        # Also check for error messages from failed tool calls
        tool_errors = []
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage) and hasattr(msg, 'content') and msg.content:
                content_str = str(msg.content)
                if 'error' in content_str.lower() or 'failed' in content_str.lower():
                    tool_errors.append(content_str)
        
        log_agent_flow("ORDERING", "Cart tool results search", {
            "total_messages": len(messages),
            "has_view_cart_result": view_cart_result is not None,
            "add_item_results_count": len(cart_tool_results),
            "tool_errors_count": len(tool_errors)
        })
        
        # FIRST: Always strip catalog from response when user is adding items
        response_content = response.content if hasattr(response, 'content') and response.content else ""
        response_has_catalog = (
            'PRODUCT CATALOG' in response_content or 
            'complete product catalog' in response_content.lower() or
            'Here is the list of all available products' in response_content or
            'Here\'s our' in response_content and 'catalog' in response_content.lower() or
            any(cat in response_content for cat in ['=== Cookie ===', '=== Protein-Bar ===', '=== Granola-Bar ==='])
        )
        
        if response_has_catalog:
            # Strip the catalog completely - user is adding items, not asking for products
            log_agent_flow("ORDERING", "Response has catalog - stripping it", {"response_length": len(response_content)})
            response_content = ""  # Clear it, will be replaced below
        
        # If we have view_cart result, use it as primary response — but not when this turn
        # still has pending tool_calls: cart ToolMessages in state are from *previous* turns only
        # until tools run, and would show a stale cart (wrong qty/total vs about-to-run add/view).
        pending_tools = bool(getattr(response, "tool_calls", None))
        if view_cart_result and not (user_adding_items and pending_tools):
            # Format a nice response with cart contents
            cart_response_text = f"I've added the items to your cart.\n\n{view_cart_result}\n\nWould you like to add anything else or proceed with your order?"
            
            # Replace after tools have run (pending_tools is false); user sees current cart only
            response = AIMessage(
                content=cart_response_text,
                tool_calls=getattr(response, 'tool_calls', None),
                id=getattr(response, 'id', None)
            )
            log_agent_flow("ORDERING", "Replaced response with cart results", {
                "has_view_cart_result": True,
                "cart_add_results_count": len(cart_tool_results),
                "user_adding_items": True
            })
        # If no view_cart result yet but response has catalog, aggressively remove it
        elif response_content and ('PRODUCT CATALOG' in response_content or 
                                   'complete product catalog' in response_content.lower() or
                                   'Here\'s our' in response_content and 'catalog' in response_content.lower() or
                                   'Here is our' in response_content and 'catalog' in response_content.lower() or
                                   any(cat in response_content for cat in ['=== Cookie ===', '=== Protein-Bar ===', '=== Granola-Bar ==='])):
            # Response has catalog - completely remove it
            # Try multiple strategies to remove catalog
            cleaned_content = response_content
            
            # Strategy 1: Remove everything before "Would you like" or similar phrases
            end_markers = [
                'Would you like',
                'What would you like',
                'What product would you like',
                'Please tell me',
                'Please mention',
                'Cart Contents',
                'Your cart'
            ]
            for marker in end_markers:
                if marker in cleaned_content:
                    parts = cleaned_content.split(marker)
                    if len(parts) > 1:
                        cleaned_content = marker + parts[-1]
                        break
            
            # Strategy 2: Remove catalog sections (lines with === or product listings)
            if 'PRODUCT CATALOG' in cleaned_content or 'complete product catalog' in cleaned_content.lower():
                lines = cleaned_content.split('\n')
                cleaned_lines = []
                in_catalog = False
                
                for line in lines:
                    if 'PRODUCT CATALOG' in line or 'complete product catalog' in line.lower() or 'Here\'s our' in line or 'Here is our' in line:
                        in_catalog = True
                        continue
                    if in_catalog:
                        if line.startswith('===') or (line.startswith('- ') and 'PKR' in line) or 'All prices are in PKR' in line:
                            continue
                        if line.strip() and not any(cat in line for cat in ['Cookie', 'Protein', 'Granola', 'Gift Box']):
                            in_catalog = False
                            cleaned_lines.append(line)
                    else:
                        cleaned_lines.append(line)
                
                cleaned_content = '\n'.join(cleaned_lines).strip()
            
            # If we cleaned something and have content, use it
            if cleaned_content and cleaned_content != response_content and len(cleaned_content) > 20:
                response = AIMessage(
                    content=cleaned_content,
                    tool_calls=getattr(response, 'tool_calls', None),
                    id=getattr(response, 'id', None)
                )
                log_agent_flow("ORDERING", "Removed catalog from response (aggressive cleaning)", {
                    "original_length": len(response_content),
                    "cleaned_length": len(cleaned_content)
                })
            else:
                # If cleaning didn't work or left nothing, create minimal response
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    # Tools were called, just acknowledge
                    response = AIMessage(
                        content="I've added the items to your cart. Please wait for the cart summary.",
                        tool_calls=getattr(response, 'tool_calls', None),
                        id=getattr(response, 'id', None)
                    )
                log_agent_flow("ORDERING", "Catalog removal - using minimal response", {})
        elif cart_tool_results:
            # Have add_item results but no view_cart - use them
            cart_content = "I've added the items to your cart.\n\n" + "\n\n".join(cart_tool_results)
            response = AIMessage(
                content=cart_content,
                tool_calls=getattr(response, 'tool_calls', None),
                id=getattr(response, 'id', None)
            )
            log_agent_flow("ORDERING", "Used add_item results", {
                "cart_results_count": len(cart_tool_results)
            })
        elif tool_errors:
            # Tools had errors - inform user
            error_response = "I'm sorry, there was an issue adding items to your cart. Please try again or check if the product names are correct.\n\nWould you like to see the available products?"
            response = AIMessage(
                content=error_response,
                tool_calls=getattr(response, 'tool_calls', None),
                id=getattr(response, 'id', None)
            )
            log_agent_flow("ORDERING", "Tool errors - informing user", {
                "error_count": len(tool_errors)
            })
        elif response_has_catalog or not response_content.strip():
            # Catalog was stripped or response is empty - provide helpful response
            # This happens when LLM generates catalog but tools are still pending
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Tools are being called, just acknowledge
                response = AIMessage(
                    content="Adding items to your cart...",
                    tool_calls=response.tool_calls,
                    id=getattr(response, 'id', None)
                )
            else:
                # No tools called, no cart results - ask what they want to add
                response = AIMessage(
                    content="What would you like to add to your cart?",
                    tool_calls=None,
                    id=getattr(response, 'id', None)
                )
            log_agent_flow("ORDERING", "Replaced empty/catalog response", {})
        
        log_agent_flow("ORDERING", "User adding items - processing response", {
            "user_adding_items": True,
            "user_asking_for_products": user_asking_for_products,
            "response_has_catalog": 'PRODUCT CATALOG' in (response.content if hasattr(response, 'content') and response.content else "") or 'complete product catalog' in (response.content.lower() if hasattr(response, 'content') and response.content else ""),
            "has_view_cart_result": 'view_cart_result' in locals() and view_cart_result is not None,
            "cart_tool_results_count": len(cart_tool_results) if 'cart_tool_results' in locals() else 0
        })
    
    has_tool_calls = bool(hasattr(response, 'tool_calls') and response.tool_calls)
    log_graph_flow("ordering_agent", "Exiting Node", {
        "intent": current_intent,
        "has_tool_calls": has_tool_calls
    })
    
    # Use Command for dynamic routing: tools -> tools, payment intent -> payment_agent, otherwise end
    # add_messages reducer will APPEND response to existing messages, preserving ALL old messages
    if has_tool_calls:
        next_node = "tools"
    elif current_intent == "payment":
        next_node = "payment_agent"
    else:
        next_node = "__end__"
    
    return create_message_update_command(
        [response],
        state=state,
        goto=next_node,
        intent=current_intent,
        active_agent="ordering_agent"
    )


class OrderingToolNodeWithState:
    """Custom tool node that injects customer_id from state into tool calls."""
    
    def __init__(self, tools):
        self.tools = tools
        self.base_tool_node = ToolNode(tools) if tools else None
    
    def invoke(self, state: ReceptionistState) -> ReceptionistState:
        """Invoke tool node with customer_id injection."""
        from langchain_core.messages import AIMessage
        
        messages = state.get("messages", [])
        customer_id = state.get("customer_id")
        
        if not messages or not self.base_tool_node:
            return state
        
        last_message = messages[-1]
        
        # Check if last message has tool calls
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return self.base_tool_node.invoke(state)
        
        # Build product name -> id mapping if needed for add_item_to_cart
        product_id_set = set()
        product_name_to_id = {}
        try:
            products = list_products()
            for product in products:
                product_id = str(product.get("product_id", "")).strip()
                product_name = str(product.get("name", "")).strip()
                if product_id:
                    product_id_set.add(product_id.lower())
                if product_id and product_name:
                    # Multiple mapping strategies:
                    # 1. Exact normalized name -> ID
                    normalized_name = " ".join(product_name.lower().split())
                    product_name_to_id[normalized_name] = product_id
                    
                    # 2. Slugified name -> ID (e.g., "chocolate-chunks-cookie" -> "cookie-chocolate")
                    import re
                    slug_name = re.sub(r'[^a-z0-9]+', '-', product_name.lower()).strip('-')
                    product_name_to_id[slug_name] = product_id
                    
                    # 3. Name without special chars -> ID
                    simple_name = re.sub(r'[^a-z0-9\s]', '', product_name.lower())
                    product_name_to_id[simple_name] = product_id
                    
            log_agent_flow("ORDERING", "Product ID mapping built", {
                "product_count": len(products),
                "mapping_count": len(product_name_to_id),
                "valid_ids": list(product_id_set)[:5]
            })
        except Exception as e:
            log_agent_flow("ORDERING", "Failed to fetch products for ID mapping", {"error": str(e)})

        # LLM often sends variants instead of canonical IDs; map to canonical before API call (backend accepts only exact IDs).
        product_id_aliases = {
            "protein-bar-almond-brownie": "protein-bar-almond",
            "almond-brownie-protein-bar": "protein-bar-almond",
            "protein-bar-peanut-butter-fudge": "protein-bar-peanut-butter",
            "protein-bar-white-chocolate-brownie": "protein-bar-white-chocolate",
            "white-chocolate-brownie-protein-bar": "protein-bar-white-chocolate",
            "granola-bar-chocolate-peanut-butter": "granola-bar-chocolate-pb",
            "chocolate-peanut-butter-granola-bar": "granola-bar-chocolate-pb",
            "chocolate-walnut-granola-bar": "granola-bar-chocolate-walnut",
            "granola-bar-crunchy-choco-grain": "granola-bar-crunchy",
            "crunchy-choco-grain-granola-bar": "granola-bar-crunchy",
            "granola-bar-coffee-pumpkin-seed": "granola-bar-coffee-pumpkin",
            "coffee-pumpkin-seed-granola-bar": "granola-bar-coffee-pumpkin",
            "cookie-chocolate-chunks": "cookie-chocolate",
            "chocolate-chunks-cookie": "cookie-chocolate",
            "cookie-peanut-butter": "cookie-pb",
            "peanut-butter-cookie": "cookie-pb",
        }

        # Inject customer_id into tool calls if missing or set to "anonymous"
        modified_tool_calls = []
        modified = False
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call.get('name', '')
            # Handle both dict and object-style tool calls
            if isinstance(tool_call, dict):
                tool_args = tool_call.get('args', {}).copy()
                tool_id = tool_call.get('id', '')
            else:
                tool_args = getattr(tool_call, 'args', {}).copy() if hasattr(tool_call, 'args') else {}
                tool_id = getattr(tool_call, 'id', '') if hasattr(tool_call, 'id') else ''
            
            # If this is a cart-related tool and customer_id is available, ALWAYS inject it
            if customer_id and tool_name in ['add_item_to_cart', 'add_items_to_cart_batch', 'view_cart', 'update_cart_quantity', 'remove_item_from_cart', 'clear_shopping_cart', 'set_delivery_address']:
                # Always override customer_id to ensure consistency with state
                previous_customer_id = tool_args.get('customer_id', 'not_set')
                tool_args['customer_id'] = customer_id
                if previous_customer_id != customer_id:
                    modified = True
                    log_agent_flow("ORDERING", "Injected customer_id into tool call", {
                        "tool": tool_name,
                        "customer_id": customer_id,
                        "previous_customer_id": previous_customer_id
                    })

            # If add_item_to_cart: map variant IDs via aliases, then product names via product_name_to_id
            if tool_name == 'add_item_to_cart':
                raw_product_id = tool_args.get('product_id')
                if raw_product_id:
                    raw_lower = str(raw_product_id).strip().lower()
                    use_id = str(raw_product_id).strip()
                    if raw_lower not in product_id_set:
                        mapped_id = product_id_aliases.get(raw_lower)
                        if mapped_id:
                            use_id = mapped_id
                            modified = True
                            log_agent_flow("ORDERING", "Mapped variant to canonical product_id", {
                                "original": raw_product_id,
                                "mapped_product_id": mapped_id
                            })
                        else:
                            import re
                            if raw_lower in product_name_to_id:
                                mapped_id = product_name_to_id[raw_lower]
                            elif " ".join(raw_lower.split()) in product_name_to_id:
                                mapped_id = product_name_to_id[" ".join(raw_lower.split())]
                            elif raw_lower.replace('-', ' ') in product_name_to_id:
                                mapped_id = product_name_to_id[raw_lower.replace('-', ' ')]
                            else:
                                simple = re.sub(r'[^a-z0-9\s]', '', raw_lower.replace('-', ' '))
                                mapped_id = product_name_to_id.get(simple)
                            if mapped_id:
                                use_id = mapped_id
                                modified = True
                                log_agent_flow("ORDERING", "Mapped product name to product_id", {
                                    "original": raw_product_id,
                                    "mapped_product_id": mapped_id
                                })
                            else:
                                log_agent_flow("ORDERING", "Could not map product - no alias or name match", {
                                    "original": raw_product_id,
                                    "available_ids": list(product_id_set)[:10]
                                })
                    tool_args['product_id'] = use_id

            # If add_items_to_cart_batch: parse items_json, map product names to IDs, re-serialize
            if tool_name == 'add_items_to_cart_batch':
                raw_json = tool_args.get('items_json') or '[]'
                try:
                    batch_items = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                except (json.JSONDecodeError, TypeError):
                    batch_items = []
                if isinstance(batch_items, list) and batch_items:
                    import re
                    mapped_batch = []
                    for ent in batch_items:
                        if not isinstance(ent, dict) or 'product_id' not in ent:
                            continue
                        pid = str(ent.get('product_id', '')).strip()
                        qty = ent.get('quantity', 1)
                        try:
                            qty = int(qty) if qty is not None else 1
                        except (TypeError, ValueError):
                            qty = 1
                        if qty < 1:
                            continue
                        raw_lower = pid.lower()
                        use_id = pid
                        if raw_lower not in product_id_set:
                            mapped_id = product_id_aliases.get(raw_lower)
                            if mapped_id:
                                use_id = mapped_id
                                modified = True
                                log_agent_flow("ORDERING", "Mapped batch item variant to canonical product_id", {"original": pid, "mapped_product_id": mapped_id})
                            else:
                                if raw_lower in product_name_to_id:
                                    mapped_id = product_name_to_id[raw_lower]
                                elif " ".join(raw_lower.split()) in product_name_to_id:
                                    mapped_id = product_name_to_id[" ".join(raw_lower.split())]
                                elif raw_lower.replace('-', ' ') in product_name_to_id:
                                    mapped_id = product_name_to_id[raw_lower.replace('-', ' ')]
                                else:
                                    simple = re.sub(r'[^a-z0-9\s]', '', raw_lower.replace('-', ' '))
                                    mapped_id = product_name_to_id.get(simple)
                                if mapped_id:
                                    use_id = mapped_id
                                    modified = True
                                    log_agent_flow("ORDERING", "Mapped batch item name to product_id", {"original": pid, "mapped_product_id": mapped_id})
                        mapped_batch.append({"product_id": use_id, "quantity": qty})
                    if mapped_batch:
                        tool_args["items_json"] = json.dumps(mapped_batch)
                        modified = True
            
            # Reconstruct tool call
            if isinstance(tool_call, dict):
                modified_tool_calls.append({
                    **tool_call,
                    'args': tool_args
                })
            else:
                # For object-style, we need to create a dict
                modified_tool_calls.append({
                    'name': tool_name,
                    'args': tool_args,
                    'id': tool_id
                })
        
        # Build state whose last message uses mapped/injected tool calls (always, for correct execution)
        if isinstance(last_message, AIMessage):
            message_for_tools = AIMessage(
                content=last_message.content,
                tool_calls=modified_tool_calls,
                id=getattr(last_message, 'id', None)
            )
        else:
            message_for_tools = AIMessage(
                content=getattr(last_message, 'content', ''),
                tool_calls=modified_tool_calls
            )
        state_for_tools = {**state, "messages": messages[:-1] + [message_for_tools]}

        # LangGraph ToolNode runs multiple tool calls in parallel. If view_cart runs before add_*
        # finishes, the user sees a stale cart. Run add/* first, then view_cart, in order.
        _names = [tc.get("name", "") for tc in modified_tool_calls if isinstance(tc, dict)]
        if not _names and modified_tool_calls:
            _names = [getattr(tc, "name", "") for tc in modified_tool_calls]
        _has_add = any(
            n in ("add_item_to_cart", "add_items_to_cart_batch")
            for n in _names
        )
        _has_view = any(n == "view_cart" for n in _names)
        if _has_add and _has_view:
            reordered = [
                c for c in modified_tool_calls if c.get("name") != "view_cart"
            ] + [c for c in modified_tool_calls if c.get("name") == "view_cart"]
            from langchain_core.runnables import RunnableConfig

            out_msgs: list[ToolMessage] = []
            cfg: RunnableConfig = {}
            for call in reordered:
                cname = call.get("name", "")
                if cname and cname not in self.base_tool_node.tools_by_name:
                    log_agent_flow("ORDERING", "Skip unknown tool in sequential run", {"name": cname})
                    continue
                injected = self.base_tool_node.inject_tool_args(call, state_for_tools, None)
                out_msgs.append(self.base_tool_node._run_one(injected, "dict", cfg))
            log_agent_flow(
                "ORDERING",
                "Sequential cart tools (add then view) to avoid parallel race",
                {"returned": len(out_msgs)},
            )
            return {"messages": out_msgs}

        if modified:
            return self.base_tool_node.invoke(state_for_tools)

        return self.base_tool_node.invoke(state)


# Combine cart tools, product tools, and calculator tools for tool node
ORDERING_TOOLS_FOR_NODE = (CART_TOOLS or []) + (PRODUCT_TOOLS or []) + (CALCULATOR_TOOLS or [])

# Create custom tool node that injects customer_id
ordering_tool_node = OrderingToolNodeWithState(ORDERING_TOOLS_FOR_NODE) if ORDERING_TOOLS_FOR_NODE else None
