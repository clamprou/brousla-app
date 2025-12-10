"""Factory to create LLM client instances based on configuration."""
from app.config import settings
from app.llm.base import LLMClient
from app.llm.openai_client import OpenAIClient


_llm_client: LLMClient = None


def get_llm_client() -> LLMClient:
    """
    Get the configured LLM client instance.
    
    Returns:
        LLMClient instance based on AI_PROVIDER setting
    """
    global _llm_client
    
    if _llm_client is None:
        provider = settings.ai_provider.lower()
        
        if provider == "openai":
            _llm_client = OpenAIClient()
        elif provider == "openai-compatible":
            # TODO: Implement OpenAICompatibleClient when needed
            # For now, fallback to OpenAI
            _llm_client = OpenAIClient()
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    return _llm_client

