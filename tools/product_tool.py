"""Product listing tool for QA agent."""
from langchain_core.tools import tool
from utils.logger import log_tool_call


@tool
def list_all_products() -> str:
    """Get a list of all available products with their prices.
    
    Use this tool when users ask about available products, product catalog, or "what products do you have".
    
    Returns:
        Formatted string with all products and their prices in PKR
    """
    log_tool_call("list_all_products", {})
    
    products = """PRODUCT CATALOG - All Available Products

=== Protein Bars (15g Protein Each) - PKR 450.00 each ===
- White Chocolate Brownie Protein Bar
- Almond Brownie Protein Bar
- Peanut Butter Fudge Protein Bar
- Fitness Fuel - Pre & Post Workout Pack (Regular: PKR 3,350.00, Sale: PKR 3,200.00)

=== Chewy Protein Mini (7g Protein) - PKR 200.00 each ===
- Chewy Protein Mini

=== Granola Bars - PKR 220.00 each ===
- Chocolate & Walnut Granola Bar
- Chocolate & Peanut Butter Granola Bar
- Coffee & Pumpkin Seed Granola Bar
- Crunchy Choco Grain Granola Bar
- 5 Granola Bars Pack (Regular: PKR 1,100.00, Sale: PKR 1,050.00)

=== Granola Cereal - PKR 800.00 each ===
- Chocolate, Fruit & Nut Granola Cereal
- Peanut Butter & Jelly Granola Cereal

=== Cookies - PKR 200.00 each ===
- Chocolate Chunks Cookie
- Peanut Butter Cookie
- Mix Cookie Box - 5 cookies (Regular: PKR 1,000.00, Sale: PKR 920.00)

=== Gift Boxes ===
- Gift Box – All Bars & Granola Cereals: PKR 4,320.00
- Gift Box - All Bars: PKR 3,580.00
- Gift Box – Protein Bars & Granola Cereal: PKR 3,150.00
- Gift Box – Granola Bars & Cereal: PKR 2,660.00

=== Special Offers ===
- Buy 5 Protein Bars, Get 1 FREE (Regular: PKR 2,700.00, Sale: PKR 2,250.00)
- Buy any 5 Granola Bars, Get 1 COOKIE FREE (Regular: PKR 1,300.00, Sale: PKR 1,100.00)

All prices are in PKR (Pakistani Rupees).
"""
    
    log_tool_call("list_all_products", {}, "Product list returned")
    return products


# Export tools list
PRODUCT_TOOLS = [list_all_products]
