"""Pydantic models for request/response validation."""
from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr


# Auth Models
class UserRegister(BaseModel):
    """User registration request model."""
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    """User response model."""
    id: str
    email: str
    email_verified: bool = False


class EmailConfirmationRequest(BaseModel):
    """Email confirmation request model."""
    token: str


class ResendConfirmationRequest(BaseModel):
    """Resend confirmation email request model."""
    email: EmailStr


class MessageResponse(BaseModel):
    """Generic message response model."""
    message: str


# AI Chat Models
class ChatMessage(BaseModel):
    """Chat message model."""
    role: Literal["user", "system", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""
    messages: List[ChatMessage]
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    stream: bool = False


class ChatResponse(BaseModel):
    """Non-streaming chat response model."""
    content: str
    model: str
    usage: Optional[dict] = None


# Prompt Generation Models
class PromptGenerationRequest(BaseModel):
    """Prompt generation request model."""
    concept: str
    number_of_clips: int
    previous_prompts: Optional[List[str]] = None
    previous_summaries: Optional[List[str]] = None


class PromptGenerationResponse(BaseModel):
    """Prompt generation response model."""
    prompts: List[str]


# Embedding and Summary Models
class EmbeddingRequest(BaseModel):
    """Embedding generation request model."""
    text: str


class EmbeddingResponse(BaseModel):
    """Embedding generation response model."""
    embedding: List[float]


class SummarizePromptsRequest(BaseModel):
    """Prompt summarization request model."""
    prompts: List[str]
    concept: str


class SummarizePromptsResponse(BaseModel):
    """Prompt summarization response model."""
    summary: str
