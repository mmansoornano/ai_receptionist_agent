"""Unified LLM service supporting multiple providers (Ollama, OpenAI, etc.)."""
from typing import Optional
try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol
from langchain_core.language_models import BaseChatModel
from config import (
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_MODEL
)


class LLMProvider(Protocol):
    """Protocol for LLM providers."""
    
    def get_llm(self, temperature: float = 0.7) -> BaseChatModel:
        """Get a LangChain-compatible LLM instance."""
        ...
    
    def supports_tools(self) -> bool:
        """Check if provider supports tool calling."""
        ...


class OllamaProvider:
    """Ollama provider for local LLM."""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    def get_llm(self, temperature: float = 0.7) -> BaseChatModel:
        """Get Ollama LLM instance."""
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                base_url=self.base_url,
                model=self.model,
                temperature=temperature,
            )
        except ImportError:
            raise ImportError(
                "langchain-ollama not installed. Install with: pip install langchain-ollama"
            )
    
    def supports_tools(self) -> bool:
        """Ollama supports tool calling with newer models."""
        # Models like llama3.1:8b, llama3.2, mistral, qwen2.5, deepseek-r1 support tool calling
        return True


class OpenAIProvider:
    """OpenAI provider for cloud LLM."""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    def get_llm(self, temperature: float = 0.7) -> BaseChatModel:
        """Get OpenAI LLM instance."""
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=self.model,
            temperature=temperature,
            api_key=self.api_key,
        )
    
    def supports_tools(self) -> bool:
        """OpenAI fully supports tool calling."""
        return True


class LLMService:
    """Unified LLM service."""
    
    def __init__(self):
        self.provider = self._create_provider()
        self.provider_name = LLM_PROVIDER
        self.model_name = OLLAMA_MODEL if LLM_PROVIDER == 'ollama' else OPENAI_MODEL
    
    def _create_provider(self) -> LLMProvider:
        """Create appropriate provider based on configuration."""
        if LLM_PROVIDER == 'ollama':
            return OllamaProvider(
                base_url=OLLAMA_BASE_URL,
                model=OLLAMA_MODEL
            )
        elif LLM_PROVIDER == 'openai':
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY required when using OpenAI provider")
            return OpenAIProvider(
                api_key=OPENAI_API_KEY,
                model=OPENAI_MODEL
            )
        else:
            raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")
    
    def get_llm(self, temperature: float = 0.7) -> BaseChatModel:
        """Get LLM instance."""
        return self.provider.get_llm(temperature=temperature)
    
    def supports_tools(self) -> bool:
        """Check if current provider supports tool calling."""
        return self.provider.supports_tools()


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
