"""OpenAI client implementation."""
from typing import List, AsyncIterator, Union
from openai import AsyncOpenAI
from app.models import ChatMessage
from app.llm.base import LLMClient
from app.config import settings


class OpenAIClient(LLMClient):
    """OpenAI API client implementation."""
    
    def __init__(self):
        """Initialize OpenAI client with API key from settings."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: float,
        stream: bool = False
    ) -> Union[AsyncIterator[str], str]:
        """
        Send chat request to OpenAI API.
        
        Args:
            messages: List of chat messages
            model: Model name (e.g., "gpt-4-turbo-preview")
            temperature: Temperature setting
            stream: Whether to stream the response
            
        Returns:
            If stream=True: AsyncIterator of response chunks
            If stream=False: Complete response string
        """
        # Convert Pydantic models to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        if stream:
            return self._stream_chat(openai_messages, model, temperature)
        else:
            return await self._non_stream_chat(openai_messages, model, temperature)
    
    async def _stream_chat(
        self,
        messages: List[dict],
        model: str,
        temperature: float
    ) -> AsyncIterator[str]:
        """Handle streaming chat responses."""
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    
    async def _non_stream_chat(
        self,
        messages: List[dict],
        model: str,
        temperature: float
    ) -> str:
        """Handle non-streaming chat responses."""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=False
        )
        
        return response.choices[0].message.content or ""

