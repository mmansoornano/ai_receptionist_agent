"""Product listing tool for QA agent."""
from collections import defaultdict
from langchain_core.tools import tool
from services.product_service import list_products
from utils.logger import log_tool_call


@tool
def list_all_products() -> str:
    """Get a list of all available products with their prices.
    
    Use this tool when users ask about available products, product catalog, or "what products do you have".
    
    Returns:
        Formatted string with all products and their prices in PKR
    """
    log_tool_call("list_all_products", {})

    products = list_products()
    if not products:
        message = "No products are available right now."
        log_tool_call("list_all_products", {}, message)
        return message

    grouped = defaultdict(list)
    for product in products:
        category = product.get("category") or "Other"
        grouped[category].append(product)

    lines = ["PRODUCT CATALOG - All Available Products"]
    for category in sorted(grouped.keys()):
        lines.append(f"\n=== {category.title()} ===")
        for item in grouped[category]:
            name = item.get("name") or item.get("product_id")
            price = item.get("price")
            if price is None:
                lines.append(f"- {name}")
            else:
                lines.append(f"- {name}: PKR {float(price):,.2f}")

    lines.append("\nAll prices are in PKR (Pakistani Rupees).")
    message = "\n".join(lines)
    log_tool_call("list_all_products", {}, "Product list returned")
    return message


# Export tools list
PRODUCT_TOOLS = [list_all_products]
