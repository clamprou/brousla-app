"""OpenAI client implementation."""
from typing import List, AsyncIterator, Union
from openai import AsyncOpenAI
from app.models import ChatMessage
from app.llm.base import LLMClient
from app.config import settings
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)


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
        
        # Pretty print logging: Log the exact request being sent to OpenAI API
        logger.debug("\n" + "╔" + "═" * 78 + "╗")
        logger.debug("║" + " " * 22 + "🔌 RAW API CALL" + " " * 44 + "║")
        logger.debug("╠" + "═" * 78 + "╣")
        logger.debug("║ " + f"📍 Endpoint: chat.completions.create".ljust(77) + "║")
        logger.debug("║ " + f"🤖 Model: {model}".ljust(77) + "║")
        logger.debug("║ " + f"🌡️  Temperature: {temperature}".ljust(77) + "║")
        logger.debug("║ " + f"📡 Stream: {stream}".ljust(77) + "║")
        logger.debug("╠" + "─" * 78 + "╣")
        logger.debug("║ " + f"📨 Messages (JSON format):".ljust(77) + "║")
        logger.debug("║ " + f"   ┌─".ljust(77) + "║")
        
        # Pretty print JSON with proper indentation
        json_str = json.dumps(openai_messages, indent=2, ensure_ascii=False)
        for line in json_str.split('\n'):
            # Truncate very long lines
            if len(line) > 70:
                logger.debug("║ " + f"   │ {line[:67]}...".ljust(77) + "║")
            else:
                logger.debug("║ " + f"   │ {line}".ljust(77) + "║")
        
        logger.debug("║ " + f"   └─".ljust(77) + "║")
        logger.debug("╚" + "═" * 78 + "╝\n")
        
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
        
        # Pretty print logging: Log the raw OpenAI API response
        content = response.choices[0].message.content or "" if response.choices else ""
        
        logger.debug("\n" + "╔" + "═" * 78 + "╗")
        logger.debug("║" + " " * 20 + "📥 RAW API RESPONSE" + " " * 40 + "║")
        logger.debug("╠" + "═" * 78 + "╣")
        logger.debug("║ " + f"🆔 Response ID: {response.id}".ljust(77) + "║")
        logger.debug("║ " + f"🤖 Model: {response.model}".ljust(77) + "║")
        logger.debug("║ " + f"📦 Object: {response.object}".ljust(77) + "║")
        logger.debug("║ " + f"🕐 Created: {response.created}".ljust(77) + "║")
        logger.debug("╠" + "─" * 78 + "╣")
        
        if hasattr(response, 'usage') and response.usage:
            logger.debug("║ " + f"💰 Token Usage:".ljust(77) + "║")
            logger.debug("║ " + f"   • Prompt Tokens: {response.usage.prompt_tokens:,}".ljust(77) + "║")
            logger.debug("║ " + f"   • Completion Tokens: {response.usage.completion_tokens:,}".ljust(77) + "║")
            logger.debug("║ " + f"   • Total Tokens: {response.usage.total_tokens:,}".ljust(77) + "║")
            logger.debug("╠" + "─" * 78 + "╣")
        
        logger.debug("║ " + f"📊 Choices: {len(response.choices)}".ljust(77) + "║")
        logger.debug("║ " + f"📏 Content Length: {len(content):,} characters".ljust(77) + "║")
        
        if content:
            logger.debug("╠" + "─" * 78 + "╣")
            logger.debug("║ " + f"📝 Content Preview:".ljust(77) + "║")
            logger.debug("║ " + f"   ┌─".ljust(77) + "║")
            
            # Show preview of content (first 30 lines or 2000 chars)
            preview_lines = content.split('\n')[:30]
            preview_text = '\n'.join(preview_lines)
            
            if len(content) > 2000:
                for line in preview_lines:
                    if len(line) > 70:
                        logger.debug("║ " + f"   │ {line[:67]}...".ljust(77) + "║")
                    else:
                        logger.debug("║ " + f"   │ {line}".ljust(77) + "║")
                logger.debug("║ " + f"   │ ... ({len(content) - len(preview_text):,} more characters) ...".ljust(77) + "║")
            else:
                for line in preview_lines:
                    if len(line) > 70:
                        logger.debug("║ " + f"   │ {line[:67]}...".ljust(77) + "║")
                    else:
                        logger.debug("║ " + f"   │ {line}".ljust(77) + "║")
            
            logger.debug("║ " + f"   └─".ljust(77) + "║")
        
        logger.debug("╚" + "═" * 78 + "╝\n")
        
        return response.choices[0].message.content or ""

