"""AI chat routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, PromptGenerationRequest, PromptGenerationResponse
from app.auth import get_current_user
from app.rate_limit import get_rate_limiter
from app.llm.factory import get_llm_client
import json
import re

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


@router.post("/generate-prompts", response_model=PromptGenerationResponse)
async def generate_prompts(
    request: PromptGenerationRequest
):
    """
    Generate diverse prompts for video clips based on a concept.
    
    This endpoint is designed for internal server-to-server calls and does not
    require authentication. It generates distinct but related prompts for each clip
    to create a cohesive multi-clip video.
    """
    if request.number_of_clips < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="number_of_clips must be at least 1"
        )
    
    if not request.concept or not request.concept.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="concept cannot be empty"
        )
    
    # Create system prompt for prompt generation
    system_prompt = f"""You are a creative video prompt generator. Your task is to generate {request.number_of_clips} distinct but related video prompts based on the following concept.

Concept: {request.concept}

Requirements:
1. Generate exactly {request.number_of_clips} different prompts
2. Each prompt should be distinct but related to the concept
3. Create a cohesive narrative flow across the prompts (they should work together as a sequence)
4. Each prompt should be detailed and descriptive for video generation
5. Return ONLY a JSON array of strings, with no additional text or explanation
6. Format: ["prompt 1", "prompt 2", "prompt 3", ...]

Example format:
["A serene sunrise over a misty mountain range with birds flying in the distance", "The same mountain range at midday with hikers on a trail", "The mountain range at sunset with a campfire in the foreground"]

Generate the prompts now:"""

    user_message = f"Generate {request.number_of_clips} video prompts for: {request.concept}"
    
    # Get LLM client
    llm_client = get_llm_client()
    
    try:
        # Generate prompts using LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response_content = await llm_client.chat(
            messages=messages,
            model="gpt-4-turbo-preview",
            temperature=0.8,  # Higher temperature for more creative variations
            stream=False
        )
        
        # Parse the response to extract prompts
        prompts = _parse_prompts_from_response(response_content, request.number_of_clips)
        
        # Validate we got the right number of prompts
        if len(prompts) != request.number_of_clips:
            # If we got wrong number, try to fix it
            if len(prompts) > request.number_of_clips:
                prompts = prompts[:request.number_of_clips]
            elif len(prompts) < request.number_of_clips:
                # Pad with variations of the last prompt or the concept
                while len(prompts) < request.number_of_clips:
                    prompts.append(prompts[-1] if prompts else request.concept)
        
        return PromptGenerationResponse(prompts=prompts)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate prompts: {str(e)}"
        )


def _parse_prompts_from_response(response: str, expected_count: int) -> list:
    """
    Parse prompts from LLM response.
    Handles various formats: JSON array, numbered list, bullet points, etc.
    """
    # Try to extract JSON array first
    json_match = re.search(r'\[.*?\]', response, re.DOTALL)
    if json_match:
        try:
            prompts = json.loads(json_match.group(0))
            if isinstance(prompts, list) and all(isinstance(p, str) for p in prompts):
                return prompts
        except json.JSONDecodeError:
            pass
    
    # Try to extract from numbered list (1. prompt, 2. prompt, etc.)
    numbered_pattern = r'(?:^|\n)\s*(?:\d+[\.\)]|\-|\*)\s*(.+?)(?=\n\s*(?:\d+[\.\)]|\-|\*)|\n\n|$)'
    matches = re.findall(numbered_pattern, response, re.MULTILINE)
    if matches and len(matches) >= expected_count:
        return [m.strip() for m in matches[:expected_count]]
    
    # Try to extract from lines (one prompt per line)
    lines = [line.strip() for line in response.split('\n') if line.strip()]
    # Filter out lines that look like metadata or instructions
    prompts = [line for line in lines if not line.lower().startswith(('example', 'format', 'requirements', 'note:'))]
    if prompts and len(prompts) >= expected_count:
        return prompts[:expected_count]
    
    # Fallback: split by common delimiters
    for delimiter in ['\n\n', '|', ';']:
        parts = [p.strip() for p in response.split(delimiter) if p.strip()]
        if len(parts) >= expected_count:
            return parts[:expected_count]
    
    # Last resort: return the whole response as a single prompt (will be handled by caller)
    return [response.strip()] if response.strip() else []

