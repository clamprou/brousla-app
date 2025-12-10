"""Base abstract interface for LLM clients."""
from abc import ABC, abstractmethod
from typing import List, AsyncIterator, Union
from app.models import ChatMessage


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float,
        stream: bool = False
    ) -> Union[AsyncIterator[str], str]:
        """
        Send a chat request to the LLM.
        
        Args:
            messages: List of chat messages
            model: Model name to use
            temperature: Temperature setting
            stream: Whether to stream the response
            
        Returns:
            If stream=True: AsyncIterator of response chunks (strings)
            If stream=False: Complete response string
        """
        pass

