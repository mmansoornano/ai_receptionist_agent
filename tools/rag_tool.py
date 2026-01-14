"""RAG tool for QA agent to retrieve information from knowledge base."""
from langchain_core.tools import tool
from services.rag_service import get_rag_service
from utils.logger import log_tool_call


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information relevant to the user's question.
    
    Use this tool when you need to answer questions about:
    - Business hours
    - Services offered
    - Contact information
    - Policies (booking, cancellation, refund)
    - General business information
    
    Args:
        query: The question or search query
    
    Returns:
        Relevant information from the knowledge base
    """
    log_tool_call("search_knowledge_base", {"query": query})
    try:
        rag_service = get_rag_service()
        chunks = rag_service.retrieve_relevant_chunks(query, k=3)
        
        if not chunks:
            result = "No relevant information found in the knowledge base."
        else:
            result = "Relevant information:\n\n" + "\n\n---\n\n".join(chunks)
        
        log_tool_call("search_knowledge_base", {"query": query}, result[:200])
        return result
    except Exception as e:
        result = f"Error searching knowledge base: {str(e)}"
        log_tool_call("search_knowledge_base", {"query": query}, result)
        return result
