"""RAG (Retrieval Augmented Generation) service for QA agent using FAISS."""
from typing import List, Optional
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_API_KEY
from utils.logger import log_tool_call

# Global RAG instance
_rag_service = None


class RAGService:
    """RAG service for document retrieval using FAISS vector store."""
    
    def __init__(self, document_path: Optional[Path] = None):
        """Initialize RAG service with document."""
        self.documents = []
        self.chunks = []
        self.embeddings = None
        self.vectorstore = None
        self.vectorstore_path = Path(__file__).parent.parent / 'data' / 'vectorstore'
        
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
        """Load and process document, create FAISS vector store."""
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
            
            # Create FAISS vector store if embeddings available
            if self.embeddings:
                try:
                    # Create vector store from documents
                    self.vectorstore = FAISS.from_documents(self.chunks, self.embeddings)
                    
                    # Save vector store
                    self.vectorstore_path.parent.mkdir(parents=True, exist_ok=True)
                    self.vectorstore.save_local(str(self.vectorstore_path))
                    
                    log_tool_call("rag_load_document", {
                        "path": str(document_path),
                        "chunks": len(self.chunks),
                        "vectorstore": "FAISS",
                        "saved": True
                    })
                except Exception as e:
                    print(f"Warning: Could not create FAISS vector store: {e}")
                    self.vectorstore = None
            else:
                print("Warning: No embeddings available, vector store not created")
                self.vectorstore = None
            
        except Exception as e:
            print(f"Error loading document: {e}")
    
    def _load_vectorstore(self):
        """Load vector store from disk if available."""
        if self.vectorstore is None and self.embeddings:
            try:
                if self.vectorstore_path.exists():
                    self.vectorstore = FAISS.load_local(
                        str(self.vectorstore_path),
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
            except Exception as e:
                print(f"Warning: Could not load vector store: {e}")
    
    def retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[str]:
        """Retrieve relevant document chunks for a query using FAISS."""
        if not self.chunks:
            return []
        
        # Load vector store if needed
        self._load_vectorstore()
        
        if self.vectorstore and self.embeddings:
            try:
                # Use FAISS similarity search
                docs = self.vectorstore.similarity_search(query, k=k)
                return [doc.page_content for doc in docs]
            except Exception as e:
                print(f"Error retrieving chunks from FAISS: {e}")
                # Fallback to keyword matching
                return self._keyword_search(query, k)
        else:
            # Fallback to keyword matching
            return self._keyword_search(query, k)
    
    def _keyword_search(self, query: str, k: int) -> List[str]:
        """Fallback keyword-based search."""
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
        # Default document path - use product knowledge
        doc_path = Path(__file__).parent.parent / 'docs' / 'product_knowledge.txt'
        _rag_service = RAGService(doc_path)
    return _rag_service
