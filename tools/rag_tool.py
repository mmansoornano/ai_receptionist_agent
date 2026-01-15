"""RAG tool for QA agent to retrieve information from knowledge base."""
from langchain_core.tools import tool
from services.rag_service import get_rag_service
from tools.slang_normalizer import preprocess_query
from utils.logger import log_tool_call


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information relevant to the user's question.
    
    Use this tool when you need to answer questions about:
    - Product information (types, prices, features, descriptions)
    - Product categories (protein bars, granola bars, cookies, cereals, gift boxes)
    - Pricing and offers
    - Product specifications and ingredients
    
    Args:
        query: The question or search query (may contain slang terms like "pp" for "price please")
    
    Returns:
        Relevant information from the knowledge base
    """
    log_tool_call("search_knowledge_base", {"query": query})
    try:
        # Normalize slang terms in query
        normalized_query = preprocess_query(query)
        if normalized_query != query:
            log_tool_call("search_knowledge_base", {"normalized": normalized_query})
        
        rag_service = get_rag_service()
        chunks = rag_service.retrieve_relevant_chunks(normalized_query, k=3)
        
        if not chunks:
            result = "No relevant information found in the knowledge base."
        else:
            result = "Relevant information:\n\n" + "\n\n---\n\n".join(chunks)
        
        log_tool_call("search_knowledge_base", {"query": query}, result)
        return result
    except Exception as e:
        result = f"Error searching knowledge base: {str(e)}"
        log_tool_call("search_knowledge_base", {"query": query}, result)
        return result
