"""RAG (Retrieval Augmented Generation) service for QA agent."""
from typing import List, Optional
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_API_KEY
from utils.logger import log_tool_call

# Global RAG instance
_rag_service = None


class RAGService:
    """RAG service for document retrieval."""
    
    def __init__(self, document_path: Optional[Path] = None):
        """Initialize RAG service with document."""
        self.documents = []
        self.chunks = []
        self.embeddings = None
        self.embeddings_list = []
        
        # Load embeddings based on provider
        if LLM_PROVIDER == 'ollama':
            try:
                from langchain_ollama import OllamaEmbeddings
                self.embeddings = OllamaEmbeddings(
                    base_url=OLLAMA_BASE_URL,
                    model=OLLAMA_MODEL
                )
            except Exception as e:
                print(f"Warning: Could not load Ollama embeddings: {e}")
                self.embeddings = None
        elif LLM_PROVIDER == 'openai' and OPENAI_API_KEY:
            try:
                from langchain_openai import OpenAIEmbeddings
                self.embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"Warning: Could not load OpenAI embeddings: {e}")
                self.embeddings = None
        
        # Load document if path provided
        if document_path:
            self.load_document(document_path)
    
    def load_document(self, document_path: Path):
        """Load and process document."""
        try:
            if not document_path.exists():
                print(f"Warning: Document not found at {document_path}")
                return
            
            # Read document
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create document
            doc = Document(page_content=content, metadata={"source": str(document_path)})
            self.documents = [doc]
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
            )
            self.chunks = text_splitter.split_documents(self.documents)
            
            # Create embeddings if available
            if self.embeddings:
                try:
                    texts = [chunk.page_content for chunk in self.chunks]
                    self.embeddings_list = self.embeddings.embed_documents(texts)
                except Exception as e:
                    print(f"Warning: Could not create embeddings: {e}")
                    self.embeddings_list = []
            else:
                self.embeddings_list = []
            
            log_tool_call("rag_load_document", {"path": str(document_path), "chunks": len(self.chunks)})
        except Exception as e:
            print(f"Error loading document: {e}")
    
    def retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[str]:
        """Retrieve relevant document chunks for a query."""
        if not self.chunks:
            return []
        
        if not self.embeddings or not self.embeddings_list:
            # Fallback: simple keyword matching
            query_lower = query.lower()
            scored_chunks = []
            for chunk in self.chunks:
                content_lower = chunk.page_content.lower()
                score = sum(1 for word in query_lower.split() if word in content_lower)
                if score > 0:
                    scored_chunks.append((score, chunk.page_content))
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            return [chunk for _, chunk in scored_chunks[:k]]
        
        try:
            # Embed query
            query_embedding = self.embeddings.embed_query(query)
            
            # Calculate similarity (cosine similarity)
            import numpy as np
            similarities = []
            for emb in self.embeddings_list:
                similarity = np.dot(query_embedding, emb) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(emb)
                )
                similarities.append(similarity)
            
            # Get top k chunks
            top_indices = np.argsort(similarities)[-k:][::-1]
            return [self.chunks[i].page_content for i in top_indices]
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            # Fallback to keyword matching
            query_lower = query.lower()
            scored_chunks = []
            for chunk in self.chunks:
                content_lower = chunk.page_content.lower()
                score = sum(1 for word in query_lower.split() if word in content_lower)
                if score > 0:
                    scored_chunks.append((score, chunk.page_content))
            scored_chunks.sort(reverse=True, key=lambda x: x[0])
            return [chunk for _, chunk in scored_chunks[:k]]


def get_rag_service() -> RAGService:
    """Get or create RAG service instance."""
    global _rag_service
    if _rag_service is None:
        # Default document path
        doc_path = Path(__file__).parent.parent / 'docs' / 'sample_knowledge.txt'
        _rag_service = RAGService(doc_path)
    return _rag_service
