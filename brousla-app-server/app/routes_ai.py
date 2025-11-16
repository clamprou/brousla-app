"""AI chat routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models import ChatRequest
from app.auth import get_current_user
from app.rate_limit import get_rate_limiter
from app.llm.factory import get_llm_client
import json

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a chat request to the LLM.
    
    Requires authentication via JWT token.
    Enforces rate limiting per user.
    
    Supports both streaming and non-streaming modes.
    """
    # Rate limiting check
    rate_limiter = get_rate_limiter()
    if not rate_limiter.is_allowed(current_user["id"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Get LLM client
    llm_client = get_llm_client()
    
    if request.stream:
        # Streaming mode: return SSE (Server-Sent Events)
        async def generate_stream():
            response = await llm_client.chat(
                messages=request.messages,
                model=request.model,
                temperature=request.temperature,
                stream=True
            )
            async for chunk in response:
                # Format as SSE
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # Non-streaming mode: return complete response
        response_content = await llm_client.chat(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            stream=False
        )
        
        return {
            "content": response_content,
            "model": request.model
        }

