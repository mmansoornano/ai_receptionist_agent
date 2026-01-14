"""Slang normalization for e-commerce queries."""
import re

# Common e-commerce slang terms
SLANG_MAPPINGS = {
    # Price-related
    'pp': 'price please',
    'price pls': 'price please',
    'price?': 'price please',
    'cost?': 'price please',
    'how much': 'price please',
    'rate': 'price',
    'rate?': 'price please',
    
    # Product-related
    'info': 'information',
    'info?': 'information please',
    'deets': 'details',
    'specs': 'specifications',
    'spec': 'specifications',
    
    # Quantity/ordering
    'qty': 'quantity',
    'amt': 'amount',
    'no.': 'number',
    'num': 'number',
    
    # Common abbreviations
    'thx': 'thanks',
    'ty': 'thank you',
    'pls': 'please',
    'plz': 'please',
    'u': 'you',
    'ur': 'your',
    'yr': 'your',
    
    # E-commerce specific
    'add to cart': 'add to cart',
    'atc': 'add to cart',
    'checkout': 'checkout',
    'co': 'checkout',
    'cart': 'cart',
    'order': 'order',
    'buy': 'purchase',
}


def normalize_slang(text: str) -> str:
    """Normalize slang terms in text to standard language.
    
    Args:
        text: Input text that may contain slang
    
    Returns:
        Normalized text with slang terms replaced
    """
    if not text:
        return text
    
    # Convert to lowercase for matching
    text_lower = text.lower()
    normalized = text
    
    # Replace slang terms (case-insensitive)
    for slang, replacement in SLANG_MAPPINGS.items():
        # Use word boundaries to match whole words only
        pattern = r'\b' + re.escape(slang) + r'\b'
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    return normalized


def preprocess_query(query: str) -> str:
    """Preprocess query for better matching.
    
    Args:
        query: User query
    
    Returns:
        Preprocessed query
    """
    if not query:
        return query
    
    # Normalize slang
    normalized = normalize_slang(query)
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized
